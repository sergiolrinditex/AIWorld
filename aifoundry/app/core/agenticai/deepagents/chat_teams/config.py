"""
Configuración específica del ChatTeamsAgent.

Todos los valores por defecto se toman del settings global (que lee de .env).
Se pueden sobreescribir con variables de entorno prefijadas CHAT_TEAMS_*.
"""

from aifoundry.app.config import settings


class ChatTeamsConfig:
    """
    Configuración del ChatTeamsAgent.
    Hereda model_name, temperature, max_tokens del .env via settings global.
    """

    # LLM — delegado al .env (LITELLM_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS)
    model_name: str = settings.litellm_model
    temperature: float = settings.default_temperature
    max_tokens: int = settings.default_max_tokens

    # Agent behavior
    timeout: int = 300  # segundos
    max_tool_retries: int = 2
    enable_streaming: bool = True
    max_history_messages: int = 50


# Singleton config
chat_teams_config = ChatTeamsConfig()