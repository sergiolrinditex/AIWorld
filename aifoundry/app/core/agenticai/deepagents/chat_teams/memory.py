"""
Memory y persistencia para el ChatTeamsAgent.

Gestiona el historial de conversaciones por thread_id.
Usa InMemorySaver de LangGraph (swap a Redis/Postgres en producción).
"""

import logging
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

# Singleton: un solo checkpointer compartido por todas las instancias
_checkpointer: Optional[MemorySaver] = None


def get_checkpointer() -> MemorySaver:
    """
    Retorna el checkpointer singleton para persistencia de conversaciones.

    En producción, reemplazar por PostgresSaver o RedisSaver.
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
        logger.info("ChatTeamsAgent memory initialized (InMemorySaver)")
    return _checkpointer


def reset_checkpointer() -> None:
    """Reset del checkpointer (útil para tests)."""
    global _checkpointer
    _checkpointer = None
    logger.info("ChatTeamsAgent memory reset")