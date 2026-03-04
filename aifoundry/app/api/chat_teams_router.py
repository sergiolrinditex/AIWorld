"""
Chat API Router — Endpoints SSE para el ChatTeamsAgent (Hefesto).

POST /chat          → StreamingResponse SSE
GET  /chat/history  → Historial de conversación
DELETE /chat/history → Limpiar historial
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import get_chat_agent

logger = logging.getLogger(__name__)

chat_teams_router = APIRouter(prefix="/chat", tags=["chat-teams"])


# ─── Request / Response schemas ───────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request body para /chat."""

    message: str = Field(description="Mensaje del usuario en lenguaje natural")
    thread_id: Optional[str] = Field(
        default=None,
        description="ID del hilo de conversación. Si no se proporciona, se genera uno nuevo.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "¿Cuál es el precio de la electricidad de Endesa en España?",
                    "thread_id": "user-123-thread-1",
                }
            ]
        }
    }


class ChatSyncResponse(BaseModel):
    """Response para /chat/sync (no-streaming)."""

    response: str
    thread_id: str
    tools_used: list[str] = Field(default_factory=list)


class HistoryMessage(BaseModel):
    """Un mensaje del historial."""

    role: str
    content: str
    tool_name: Optional[str] = None


class HistoryResponse(BaseModel):
    """Response para /chat/history."""

    thread_id: str
    messages: list[HistoryMessage]
    count: int


# ─── Endpoints ─────────────────────────────────────────────────────────────────


@chat_teams_router.post("")
async def chat_stream(request: ChatRequest):
    """
    Envía un mensaje al ChatTeamsAgent y recibe una respuesta como SSE stream.

    Cada evento SSE tiene el formato:
    ```
    data: {"type": "thinking|tool_start|tool_result|text|done|error", "data": "...", ...}
    ```

    Event types:
    - `thinking` — El agente está razonando
    - `tool_start` — Se inicia la ejecución de una herramienta
    - `tool_result` — Resultado de la herramienta
    - `text` — Texto completo de la respuesta final
    - `done` — Completado (incluye thread_id)
    - `error` — Error durante la ejecución
    """
    agent = get_chat_agent()
    thread_id = request.thread_id or str(uuid.uuid4())

    async def event_generator():
        async for event in agent.chat(message=request.message, thread_id=thread_id):
            yield event.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_teams_router.post("/sync", response_model=ChatSyncResponse)
async def chat_sync(request: ChatRequest):
    """
    Versión síncrona (no-streaming) del chat.
    Espera a que el agente complete y devuelve la respuesta completa.
    Útil para integraciones que no soportan SSE.
    """
    agent = get_chat_agent()
    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        result = await agent.chat_sync(message=request.message, thread_id=thread_id)
        return ChatSyncResponse(**result)
    except Exception as e:
        logger.error(f"Chat sync error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)[:500]}")


@chat_teams_router.get("/history/{thread_id}", response_model=HistoryResponse)
async def get_history(thread_id: str):
    """Obtiene el historial de mensajes de un thread."""
    agent = get_chat_agent()
    history = await agent.get_history(thread_id)

    messages = [HistoryMessage(**msg) for msg in history]

    return HistoryResponse(
        thread_id=thread_id,
        messages=messages,
        count=len(messages),
    )


@chat_teams_router.delete("/history/{thread_id}")
async def delete_history(thread_id: str):
    """
    Limpia el historial de un thread.
    Nota: Con InMemorySaver esto es un no-op (el thread simplemente no se reutiliza).
    En producción con persistencia real, aquí se borrarían los datos.
    """
    return {
        "status": "ok",
        "thread_id": thread_id,
        "message": "Thread cleared. Use a new thread_id for a fresh conversation.",
    }