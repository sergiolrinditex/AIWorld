"""
Streaming de eventos SSE para el ChatTeamsAgent.

Define los tipos de evento y el formato de serialización para Server-Sent Events.
"""

import json
import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Tipos de evento que emite el ChatTeamsAgent via SSE."""

    # El agente está pensando / razonando
    THINKING = "thinking"
    # Se va a ejecutar una herramienta
    TOOL_START = "tool_start"
    # Resultado de una herramienta
    TOOL_RESULT = "tool_result"
    # Texto parcial de la respuesta (streaming)
    TEXT_DELTA = "text_delta"
    # Texto completo final
    TEXT = "text"
    # Agente completó la ejecución
    DONE = "done"
    # Error
    ERROR = "error"


class ChatEvent(BaseModel):
    """Evento individual emitido durante streaming SSE."""

    type: EventType
    data: Any = None
    timestamp: float = Field(default_factory=time.time)
    # Metadata opcional
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    thread_id: Optional[str] = None

    def to_sse(self) -> str:
        """Serializa el evento como SSE (Server-Sent Event) string."""
        payload = self.model_dump(exclude_none=True)
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def thinking_event(content: str) -> ChatEvent:
    """Crea un evento de tipo THINKING."""
    return ChatEvent(type=EventType.THINKING, data=content)


def tool_start_event(tool_name: str, tool_args: dict) -> ChatEvent:
    """Crea un evento de tipo TOOL_START."""
    return ChatEvent(
        type=EventType.TOOL_START,
        data=f"Ejecutando {tool_name}...",
        tool_name=tool_name,
        tool_args=tool_args,
    )


def tool_result_event(tool_name: str, result: str) -> ChatEvent:
    """Crea un evento de tipo TOOL_RESULT."""
    return ChatEvent(
        type=EventType.TOOL_RESULT,
        data=result,
        tool_name=tool_name,
    )


def text_delta_event(content: str) -> ChatEvent:
    """Crea un evento de texto parcial (streaming token a token)."""
    return ChatEvent(type=EventType.TEXT_DELTA, data=content)


def text_event(content: str) -> ChatEvent:
    """Crea un evento con el texto completo final."""
    return ChatEvent(type=EventType.TEXT, data=content)


def done_event(thread_id: str) -> ChatEvent:
    """Crea un evento de finalización."""
    return ChatEvent(type=EventType.DONE, data="completed", thread_id=thread_id)


def error_event(error: str) -> ChatEvent:
    """Crea un evento de error."""
    return ChatEvent(type=EventType.ERROR, data=error)