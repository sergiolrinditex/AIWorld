"""
ChatTeamsAgent — Deep Agent conversacional para Hefesto (Microsoft Teams).

Orquesta ScraperAgents como sub-agentes y ofrece streaming SSE.
"""


def __getattr__(name: str):
    """Lazy import para evitar ImportError si deepagents no está instalado."""
    if name == "ChatTeamsAgent":
        from aifoundry.app.core.agenticai.deepagents.chat_teams.agent import ChatTeamsAgent

        return ChatTeamsAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ChatTeamsAgent"]
