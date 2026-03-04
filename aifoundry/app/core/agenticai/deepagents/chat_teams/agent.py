"""
ChatTeamsAgent — Deep Agent conversacional para Hefesto.

Usa ``create_deep_agent`` de la librería ``deepagents``
(el approach "batteries-included" de LangChain para agentes complejos).
deepagents proporciona: subagent-spawning, long-term memory, context compression.

Arquitectura:
- LLM: ChatOpenAI apuntando a LiteLLM proxy (configurable via .env)
- Tools: ScraperAgent wrappers + MCP directos (Brave Search, Playwright)
- Memory: InMemorySaver (checkpoints por thread_id)
- Streaming: astream_events v2 → ChatEvent SSE
"""

import json
import logging
import uuid
from typing import Any, AsyncIterator, Optional

from deepagents import create_deep_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from aifoundry.app.config import settings
from aifoundry.app.core.agenticai.deepagents.chat_teams.config import chat_teams_config
from aifoundry.app.core.agenticai.deepagents.chat_teams.memory import get_checkpointer
from aifoundry.app.core.agenticai.deepagents.chat_teams.prompts import get_system_prompt
from aifoundry.app.core.agenticai.deepagents.chat_teams.streaming import (
    ChatEvent,
    done_event,
    error_event,
    text_event,
    thinking_event,
    tool_result_event,
    tool_start_event,
)
from aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor import ToolResolver

logger = logging.getLogger(__name__)


def _sanitize_tool_args(obj: Any) -> Any:
    """
    Sanitiza los argumentos de tools para que sean JSON-serializables.

    Los eventos de LangGraph pueden contener objetos internos como
    AsyncCallbackManager, ToolRuntime, etc. que no son serializables.
    Esta función convierte recursivamente todo a tipos primitivos.
    """
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return {str(k): _sanitize_tool_args(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_tool_args(item) for item in obj]
    # Cualquier otro objeto → convertir a string
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


class ChatTeamsAgent:
    """
    Agente conversacional para Microsoft Teams (Hefesto).

    Usa Deep Agent (deepagents library) con:
    - Tools que wrappean ScraperAgents existentes
    - MCP tools directas para queries ad-hoc
    - Memory por thread_id (InMemorySaver)
    - Streaming SSE de eventos (thinking, tool_start, tool_result, text, done)
    """

    def __init__(self):
        self._agent = None
        self._tool_resolver: Optional[ToolResolver] = None
        self._system_prompt = None

    async def _ensure_agent(self):
        """Inicializa el agente lazy (una sola vez), incluyendo MCP tools."""
        if self._agent is not None:
            return

        # Cargar tools locales + MCP via ToolResolver (mismo patrón que ScraperAgent)
        self._tool_resolver = ToolResolver()
        tools = await self._tool_resolver.resolve_tools()

        # LLM via LiteLLM proxy (compatible con ChatOpenAI)
        llm = ChatOpenAI(
            model=settings.litellm_model,
            base_url=settings.litellm_api_base,
            api_key=settings.litellm_api_key,
            temperature=chat_teams_config.temperature,
            max_tokens=chat_teams_config.max_tokens,
            default_headers={"User-Agent": "hefesto/chat-teams-agent"},
        )

        # Memory: singleton checkpointer compartido
        checkpointer = get_checkpointer()

        # System prompt
        self._system_prompt = get_system_prompt()

        # Crear Deep Agent (deepagents library — batteries-included)
        self._agent = create_deep_agent(
            model=llm,
            tools=tools,
            system_prompt=self._system_prompt,
            checkpointer=checkpointer,
            name="hefesto-chat-teams",
        )

        logger.info(
            f"ChatTeamsAgent initialized with deepagents.create_deep_agent: "
            f"{len(tools)} tools, model={settings.litellm_model}"
        )

    async def cleanup(self):
        """Limpia recursos (MCP client via ToolResolver). Mismo patrón que ScraperAgent."""
        if self._tool_resolver:
            await self._tool_resolver.cleanup()
            self._tool_resolver = None

    async def chat(
        self,
        message: str,
        thread_id: Optional[str] = None,
    ) -> AsyncIterator[ChatEvent]:
        """
        Procesa un mensaje del usuario con streaming de eventos.

        Args:
            message: Mensaje del usuario en lenguaje natural
            thread_id: ID del hilo de conversación (se genera uno si no se proporciona)

        Yields:
            ChatEvent — eventos SSE (thinking, tool_start, tool_result, text, done/error)
        """
        await self._ensure_agent()

        if not thread_id:
            thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Emit thinking event
            yield thinking_event("Analizando tu consulta...")

            # Stream through the deep agent
            final_text = ""
            async for event in self._agent.astream_events(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                # Tool invocation start
                if kind == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = data.get("input", {})
                    if isinstance(tool_input, str):
                        tool_args = {"query": tool_input}
                    elif isinstance(tool_input, dict):
                        tool_args = _sanitize_tool_args(tool_input)
                    else:
                        tool_args = {"input": str(tool_input)}
                    yield tool_start_event(tool_name, tool_args)

                # Tool invocation end
                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    output = data.get("output", "")
                    result_str = str(output)
                    if len(result_str) > 2000:
                        result_str = result_str[:2000] + "... [truncado]"
                    yield tool_result_event(tool_name, result_str)

                # LLM streaming tokens (respuesta final)
                elif kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        if isinstance(chunk.content, str):
                            final_text += chunk.content

            # Emit final text
            if final_text:
                yield text_event(final_text)

            yield done_event(thread_id)

        except Exception as e:
            logger.error(f"ChatTeamsAgent error: {e}", exc_info=True)
            yield error_event(f"Error procesando tu mensaje: {str(e)[:500]}")

    async def chat_sync(
        self,
        message: str,
        thread_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Versión síncrona (no-streaming) de chat.
        Útil para tests y llamadas internas.

        Returns:
            Dict con keys: response, thread_id, tools_used
        """
        await self._ensure_agent()

        if not thread_id:
            thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id}}

        result = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )

        # Extraer respuesta del AI
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        response = ai_messages[-1].content if ai_messages else "Sin respuesta"

        # Extraer tools usadas
        tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        tools_used = [m.name for m in tool_messages if hasattr(m, "name")]

        return {
            "response": response,
            "thread_id": thread_id,
            "tools_used": tools_used,
        }

    async def get_history(self, thread_id: str) -> list[dict]:
        """
        Obtiene el historial de mensajes de un thread.

        Returns:
            Lista de dicts con role y content.
        """
        await self._ensure_agent()
        config = {"configurable": {"thread_id": thread_id}}

        try:
            state = await self._agent.aget_state(config)
            messages = state.values.get("messages", [])
            history = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    if msg.content:
                        history.append({"role": "assistant", "content": msg.content})
                elif isinstance(msg, ToolMessage):
                    history.append({
                        "role": "tool",
                        "tool_name": getattr(msg, "name", "unknown"),
                        "content": str(msg.content)[:500],
                    })
            return history
        except Exception as e:
            logger.warning(f"Could not retrieve history for thread {thread_id}: {e}")
            return []


# Singleton global
_agent_instance: Optional[ChatTeamsAgent] = None


def get_chat_agent() -> ChatTeamsAgent:
    """Retorna la instancia singleton del ChatTeamsAgent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ChatTeamsAgent()
    return _agent_instance