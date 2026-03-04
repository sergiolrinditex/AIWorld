"""
Tests unitarios para ChatTeamsAgent y sus componentes.

Usa mocks para deepagents.create_deep_agent y ScraperAgent — no requiere servidores MCP ni LLM real.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aifoundry.app.core.agenticai.deepagents.chat_teams.streaming import (
    ChatEvent,
    EventType,
    done_event,
    error_event,
    text_event,
    thinking_event,
    tool_result_event,
    tool_start_event,
)


# ─── Tests de streaming.py (ChatEvent / factories) ────────────────────────────


class TestChatEvent:
    """Tests para ChatEvent y sus factories."""

    def test_thinking_event(self):
        ev = thinking_event("Procesando...")
        assert ev.type == EventType.THINKING
        assert ev.data == "Procesando..."

    def test_tool_start_event(self):
        ev = tool_start_event("search_electricity", {"query": "precio luz"})
        assert ev.type == EventType.TOOL_START
        assert ev.tool_name == "search_electricity"
        assert ev.tool_args == {"query": "precio luz"}
        assert "search_electricity" in ev.data

    def test_tool_result_event(self):
        ev = tool_result_event("search_salary", "Salario medio: 25k€")
        assert ev.type == EventType.TOOL_RESULT
        assert ev.tool_name == "search_salary"
        assert "25k€" in ev.data

    def test_text_event(self):
        ev = text_event("El precio de la electricidad es 0.15€/kWh")
        assert ev.type == EventType.TEXT
        assert "0.15€/kWh" in ev.data

    def test_done_event(self):
        ev = done_event("thread-abc")
        assert ev.type == EventType.DONE
        assert ev.thread_id == "thread-abc"
        assert ev.data == "completed"

    def test_error_event(self):
        ev = error_event("Timeout en el scraper")
        assert ev.type == EventType.ERROR
        assert "Timeout" in ev.data

    def test_to_sse_format(self):
        ev = text_event("Hola mundo")
        sse = ev.to_sse()
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")
        # Debe ser JSON válido después de "data: "
        payload = json.loads(sse[len("data: ") :].strip())
        assert payload["type"] == "text"
        assert payload["data"] == "Hola mundo"
        assert "timestamp" in payload

    def test_to_sse_excludes_none(self):
        ev = thinking_event("Pensando")
        sse = ev.to_sse()
        payload = json.loads(sse[len("data: ") :].strip())
        assert "tool_name" not in payload
        assert "tool_args" not in payload
        assert "thread_id" not in payload

    def test_event_type_values(self):
        """Verifica que todos los EventType tienen valores string esperados."""
        assert EventType.THINKING.value == "thinking"
        assert EventType.TOOL_START.value == "tool_start"
        assert EventType.TOOL_RESULT.value == "tool_result"
        assert EventType.TEXT_DELTA.value == "text_delta"
        assert EventType.TEXT.value == "text"
        assert EventType.DONE.value == "done"
        assert EventType.ERROR.value == "error"


# ─── Tests de tools.py ────────────────────────────────────────────────────────


class TestTools:
    """Tests para las tools del ChatTeamsAgent."""

    def test_get_chat_teams_tools_returns_list(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import get_chat_teams_tools

        tools = get_chat_teams_tools()
        assert isinstance(tools, list)
        assert len(tools) == 4

    def test_tool_names(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import get_chat_teams_tools

        tools = get_chat_teams_tools()
        names = [t.name for t in tools]
        assert "search_electricity" in names
        assert "search_salary" in names
        assert "search_social_comments" in names
        assert "list_available_agents" in names

    def test_tools_have_descriptions(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import get_chat_teams_tools

        tools = get_chat_teams_tools()
        for t in tools:
            assert t.description, f"Tool {t.name} missing description"
            assert len(t.description) > 20, f"Tool {t.name} description too short"

    @pytest.mark.asyncio
    async def test_list_available_agents_tool(self):
        """list_available_agents debe retornar info de los 3 dominios."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import list_available_agents

        result = await list_available_agents.ainvoke({})
        assert "electricity" in result
        assert "salary" in result
        assert "social_comments" in result
        assert "Agentes disponibles" in result

    def test_load_domain_config_electricity(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _load_domain_config

        config = _load_domain_config("electricity")
        assert "product" in config
        # El config puede tener "countries" (estructura nueva) o "providers_by_country" (vieja)
        has_providers = "providers_by_country" in config or "countries" in config
        assert has_providers, f"Config keys: {list(config.keys())}"

    def test_load_domain_config_salary(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _load_domain_config

        config = _load_domain_config("salary")
        assert "product" in config
        # El product puede estar en español ("salarios") o inglés ("salary")
        product_lower = config["product"].lower()
        assert "salari" in product_lower, f"product was: {config['product']}"

    def test_load_domain_config_social(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _load_domain_config

        config = _load_domain_config("social_comments")
        assert "social_networks" in config
        assert "Instagram" in config["social_networks"]

    def test_load_domain_config_not_found(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _load_domain_config

        with pytest.raises(FileNotFoundError):
            _load_domain_config("nonexistent_domain")

    @pytest.mark.asyncio
    async def test_tool_resolver_mcp_timeout(self):
        """ToolResolver.resolve_tools() debe retornar solo tools locales si MCP se cuelga (timeout)."""
        import asyncio

        import aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor as te_mod
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor import ToolResolver

        # Simular MCP que se cuelga
        mock_client = MagicMock()

        async def hanging_get_tools():
            await asyncio.sleep(999)  # Se cuelga indefinidamente

        mock_client.get_tools = hanging_get_tools

        # Guardamos el timeout original
        original_timeout = te_mod._MCP_CONNECT_TIMEOUT

        with patch(
            "aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor.get_mcp_configs",
            return_value={"brave": {"transport": "streamable_http", "url": "http://fake"}},
        ), patch(
            "aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor.MultiServerMCPClient",
            return_value=mock_client,
        ):
            te_mod._MCP_CONNECT_TIMEOUT = 0.1  # 100ms timeout para test rápido
            try:
                resolver = ToolResolver(use_mcp=True)
                tools = await resolver.resolve_tools()
            finally:
                te_mod._MCP_CONNECT_TIMEOUT = original_timeout

        # Debe retornar solo las tools locales (4 tools)
        assert len(tools) == 4
        names = [t.name for t in tools]
        assert "search_electricity" in names

    @pytest.mark.asyncio
    async def test_run_scraper_timeout(self):
        """_run_scraper debe retornar error si ScraperAgent se cuelga (timeout)."""
        import asyncio

        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _run_scraper

        # Mock ScraperAgent que se cuelga
        mock_agent = MagicMock()

        async def hanging_run(*args, **kwargs):
            await asyncio.sleep(999)

        mock_agent.run = hanging_run
        mock_agent.__aenter__ = AsyncMock(return_value=mock_agent)
        mock_agent.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "aifoundry.app.core.agenticai.deepagents.chat_teams.tools.ScraperAgent",
            return_value=mock_agent,
        ), patch(
            "aifoundry.app.core.agenticai.deepagents.chat_teams.tools._SCRAPER_TIMEOUT",
            0.1,  # 100ms timeout para test rápido
        ):
            result = await _run_scraper("electricity", "precio luz")

        assert "tardó demasiado" in result
        assert "MCP" in result

    def test_add_date_context_no_year(self):
        """Si la query no tiene año, se añade la fecha actual."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _add_date_context

        result = _add_date_context("precio electricidad Endesa España")
        assert "(fecha actual:" in result
        assert "Endesa" in result

    def test_add_date_context_with_year(self):
        """Si la query ya tiene un año (202x/203x), NO se añade fecha."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _add_date_context

        result = _add_date_context("salario Zara 2026")
        assert "(fecha actual:" not in result
        assert "2026" in result

    def test_add_date_context_with_2025(self):
        """Año 2025 tampoco se duplica."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _add_date_context

        result = _add_date_context("precios energía 2025")
        assert "(fecha actual:" not in result

    def test_add_date_context_contains_current_year(self):
        """La fecha añadida contiene el año actual."""
        import datetime

        from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import _add_date_context

        result = _add_date_context("precio luz")
        current_year = str(datetime.datetime.now().year)
        assert current_year in result


# ─── Tests de prompts.py ──────────────────────────────────────────────────────


class TestPrompts:
    """Tests para la generación de prompts."""

    def test_get_system_prompt_not_empty(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.prompts import get_system_prompt

        prompt = get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_prompt_mentions_hefesto(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.prompts import get_system_prompt

        prompt = get_system_prompt().lower()
        assert "hefesto" in prompt

    def test_prompt_mentions_tools(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.prompts import get_system_prompt

        prompt = get_system_prompt().lower()
        # Debe mencionar los tipos de búsqueda
        assert "electric" in prompt or "salari" in prompt or "social" in prompt


# ─── Tests de memory.py ───────────────────────────────────────────────────────


class TestMemory:
    """Tests para la configuración de memoria."""

    def test_get_checkpointer_returns_instance(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.memory import get_checkpointer

        cp = get_checkpointer()
        assert cp is not None

    def test_get_checkpointer_singleton(self):
        """El checkpointer debe ser singleton."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.memory import get_checkpointer

        cp1 = get_checkpointer()
        cp2 = get_checkpointer()
        assert cp1 is cp2


# ─── Tests de config.py ───────────────────────────────────────────────────────


class TestChatTeamsConfig:
    """Tests para la configuración del ChatTeamsAgent."""

    def test_config_has_temperature(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.config import chat_teams_config

        assert hasattr(chat_teams_config, "temperature")
        assert 0 <= chat_teams_config.temperature <= 2

    def test_config_has_max_tokens(self):
        from aifoundry.app.core.agenticai.deepagents.chat_teams.config import chat_teams_config

        assert hasattr(chat_teams_config, "max_tokens")
        assert chat_teams_config.max_tokens > 0


# ─── Tests de tool_executor.py ────────────────────────────────────────────────


class TestToolResolver:
    """Tests para ToolResolver del ChatTeamsAgent."""

    @pytest.mark.asyncio
    async def test_resolve_tools_local_only(self):
        """ToolResolver sin MCP debe retornar solo tools locales."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor import ToolResolver

        resolver = ToolResolver(use_mcp=False)
        tools = await resolver.resolve_tools()
        assert len(tools) == 4
        names = [t.name for t in tools]
        assert "search_electricity" in names
        assert "list_available_agents" in names

    @pytest.mark.asyncio
    async def test_resolve_tools_custom(self):
        """ToolResolver con custom_tools debe retornar esas tools."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor import ToolResolver

        mock_tool = MagicMock()
        mock_tool.name = "custom_tool"
        resolver = ToolResolver(use_mcp=False, custom_tools=[mock_tool])
        tools = await resolver.resolve_tools()
        assert len(tools) == 1
        assert tools[0].name == "custom_tool"

    @pytest.mark.asyncio
    async def test_cleanup_without_init(self):
        """cleanup() sin haber resuelto tools no debe fallar."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.tool_executor import ToolResolver

        resolver = ToolResolver()
        await resolver.cleanup()  # No debe lanzar excepción


# ─── Tests del ChatTeamsAgent (mockeado) ──────────────────────────────────────


def _mock_tool_resolver():
    """Helper: crea un mock de ToolResolver para tests del ChatTeamsAgent."""
    mock_resolver_instance = MagicMock()
    mock_resolver_instance.resolve_tools = AsyncMock(return_value=[])
    mock_resolver_instance.cleanup = AsyncMock()
    mock_resolver_cls = MagicMock(return_value=mock_resolver_instance)
    return mock_resolver_cls, mock_resolver_instance


class TestChatTeamsAgent:
    """Tests para ChatTeamsAgent con mocks."""

    @pytest.mark.asyncio
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.create_deep_agent")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ToolResolver")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ChatOpenAI")
    async def test_chat_yields_events(self, mock_llm_cls, mock_resolver_cls, mock_create_agent):
        """chat() debe emitir al menos thinking + text/done events."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import ChatTeamsAgent

        # Mock ToolResolver
        mock_resolver = MagicMock()
        mock_resolver.resolve_tools = AsyncMock(return_value=[])
        mock_resolver.cleanup = AsyncMock()
        mock_resolver_cls.return_value = mock_resolver

        mock_llm_cls.return_value = MagicMock()

        # Mock deep agent astream_events
        mock_agent = MagicMock()

        async def fake_stream(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Respuesta de prueba")},
            }

        mock_agent.astream_events = fake_stream
        mock_create_agent.return_value = mock_agent

        agent = ChatTeamsAgent()
        events = []
        async for event in agent.chat("Hola", thread_id="test-thread"):
            events.append(event)

        types = [e.type for e in events]
        assert EventType.THINKING in types
        assert EventType.TEXT in types
        assert EventType.DONE in types

    @pytest.mark.asyncio
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.create_deep_agent")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ToolResolver")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ChatOpenAI")
    async def test_chat_handles_error(self, mock_llm_cls, mock_resolver_cls, mock_create_agent):
        """chat() debe emitir error_event si el agente falla."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import ChatTeamsAgent

        mock_resolver = MagicMock()
        mock_resolver.resolve_tools = AsyncMock(return_value=[])
        mock_resolver.cleanup = AsyncMock()
        mock_resolver_cls.return_value = mock_resolver

        mock_llm_cls.return_value = MagicMock()

        mock_agent = MagicMock()

        async def failing_stream(*args, **kwargs):
            raise RuntimeError("LLM unavailable")
            yield  # noqa: unreachable — necesario para que sea async generator

        mock_agent.astream_events = failing_stream
        mock_create_agent.return_value = mock_agent

        agent = ChatTeamsAgent()
        events = []
        async for event in agent.chat("Hola", thread_id="test-err"):
            events.append(event)

        types = [e.type for e in events]
        assert EventType.ERROR in types

    @pytest.mark.asyncio
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.create_deep_agent")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ToolResolver")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ChatOpenAI")
    async def test_chat_tool_events(self, mock_llm_cls, mock_resolver_cls, mock_create_agent):
        """chat() debe emitir tool_start y tool_result para invocaciones de tools."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import ChatTeamsAgent

        mock_resolver = MagicMock()
        mock_resolver.resolve_tools = AsyncMock(return_value=[])
        mock_resolver.cleanup = AsyncMock()
        mock_resolver_cls.return_value = mock_resolver

        mock_llm_cls.return_value = MagicMock()

        mock_agent = MagicMock()

        async def fake_stream(*args, **kwargs):
            yield {
                "event": "on_tool_start",
                "name": "search_electricity",
                "data": {"input": {"query": "precio luz España"}},
            }
            yield {
                "event": "on_tool_end",
                "name": "search_electricity",
                "data": {"output": "Precio: 0.15€/kWh"},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="El precio es 0.15€/kWh")},
            }

        mock_agent.astream_events = fake_stream
        mock_create_agent.return_value = mock_agent

        agent = ChatTeamsAgent()
        events = []
        async for event in agent.chat("Precio electricidad", thread_id="test-tools"):
            events.append(event)

        types = [e.type for e in events]
        assert EventType.TOOL_START in types
        assert EventType.TOOL_RESULT in types
        assert EventType.TEXT in types

    @pytest.mark.asyncio
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.create_deep_agent")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ToolResolver")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ChatOpenAI")
    async def test_chat_sync_returns_dict(self, mock_llm_cls, mock_resolver_cls, mock_create_agent):
        """chat_sync() debe retornar dict con response, thread_id, tools_used."""
        from langchain_core.messages import AIMessage

        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import ChatTeamsAgent

        mock_resolver = MagicMock()
        mock_resolver.resolve_tools = AsyncMock(return_value=[])
        mock_resolver.cleanup = AsyncMock()
        mock_resolver_cls.return_value = mock_resolver

        mock_llm_cls.return_value = MagicMock()

        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "messages": [AIMessage(content="Respuesta sincrónica de prueba")],
            }
        )
        mock_create_agent.return_value = mock_agent

        agent = ChatTeamsAgent()
        result = await agent.chat_sync("Hola sync", thread_id="test-sync")

        assert "response" in result
        assert "thread_id" in result
        assert "tools_used" in result
        assert result["response"] == "Respuesta sincrónica de prueba"
        assert result["thread_id"] == "test-sync"

    @pytest.mark.asyncio
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.create_deep_agent")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ToolResolver")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ChatOpenAI")
    async def test_get_history_returns_list(self, mock_llm_cls, mock_resolver_cls, mock_create_agent):
        """get_history() debe retornar lista de mensajes."""
        from langchain_core.messages import AIMessage, HumanMessage

        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import ChatTeamsAgent

        mock_resolver = MagicMock()
        mock_resolver.resolve_tools = AsyncMock(return_value=[])
        mock_resolver.cleanup = AsyncMock()
        mock_resolver_cls.return_value = mock_resolver

        mock_llm_cls.return_value = MagicMock()

        mock_state = MagicMock()
        mock_state.values = {
            "messages": [
                HumanMessage(content="Hola"),
                AIMessage(content="Hola, soy Hefesto"),
            ]
        }

        mock_agent = MagicMock()
        mock_agent.aget_state = AsyncMock(return_value=mock_state)
        mock_create_agent.return_value = mock_agent

        agent = ChatTeamsAgent()
        history = await agent.get_history("test-history")

        assert isinstance(history, list)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_get_chat_agent_singleton(self):
        """get_chat_agent() retorna siempre la misma instancia."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import get_chat_agent

        # Reset singleton para test limpio
        import aifoundry.app.core.agenticai.deepagents.chat_teams.agent as agent_mod

        agent_mod._agent_instance = None

        a1 = get_chat_agent()
        a2 = get_chat_agent()
        assert a1 is a2

        # Cleanup
        agent_mod._agent_instance = None

    @pytest.mark.asyncio
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.create_deep_agent")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ToolResolver")
    @patch("aifoundry.app.core.agenticai.deepagents.chat_teams.agent.ChatOpenAI")
    async def test_cleanup_tool_resolver(self, mock_llm_cls, mock_resolver_cls, mock_create_agent):
        """cleanup() debe llamar a ToolResolver.cleanup() y resetear el resolver."""
        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import ChatTeamsAgent

        mock_resolver = MagicMock()
        mock_resolver.resolve_tools = AsyncMock(return_value=[])
        mock_resolver.cleanup = AsyncMock()
        mock_resolver_cls.return_value = mock_resolver

        mock_llm_cls.return_value = MagicMock()
        mock_create_agent.return_value = MagicMock()

        agent = ChatTeamsAgent()
        await agent._ensure_agent()

        assert agent._tool_resolver is mock_resolver
        await agent.cleanup()
        mock_resolver.cleanup.assert_called_once()
        assert agent._tool_resolver is None