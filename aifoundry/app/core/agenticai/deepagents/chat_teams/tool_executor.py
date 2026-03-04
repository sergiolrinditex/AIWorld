"""
Módulo de resolución de tools para el ChatTeamsAgent.

Encapsula la lógica de carga de tools locales y MCP,
incluyendo la configuración de error handlers y timeouts.

Sigue el mismo patrón que ``aiagents/scraper/tool_executor.py``
para mantener consistencia en la arquitectura del proyecto.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from aifoundry.app.core.agenticai.deepagents.chat_teams.tools import get_chat_teams_tools

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Timeout para conexiones MCP (segundos)
_MCP_CONNECT_TIMEOUT = 15


# =============================================================================
# ERROR PATTERNS (usados por el tool error handler)
# =============================================================================

_NO_DATA_PATTERNS = (
    "no web results",
    "no results found",
    "timed out",
)


def _is_no_data_error(text: str) -> bool:
    """Verifica si el error indica simplemente que no se encontraron datos."""
    if not text:
        return False
    text_lower = text.lower()
    return any(p in text_lower for p in _NO_DATA_PATTERNS)


def _tool_error_handler(error: Exception) -> str:
    """
    Handler para errores de tools MCP.

    Devuelve un mensaje amigable al LLM para que pueda decidir
    qué hacer (cambiar query, continuar con datos existentes, etc.)
    en vez de crashear todo el agente.
    """
    error_str = str(error)
    if _is_no_data_error(error_str):
        return (
            "No se encontraron resultados web para esta consulta. "
            "Intenta con una query diferente o continúa con los datos que ya tienes."
        )
    return f"Error en herramienta: {error_str[:500]}"


# =============================================================================
# MCP CONFIG LOADER
# =============================================================================

def get_mcp_configs() -> Dict[str, Dict]:
    """
    Obtiene las configuraciones de los MCPs disponibles.

    Reutiliza las configs del ScraperAgent para mantener consistencia.
    """
    from aifoundry.app.mcp_servers.externals.brave_search.brave_search_mcp import (
        get_mcp_config as get_brave_config,
    )
    from aifoundry.app.mcp_servers.externals.playwright.playwright_mcp import (
        get_mcp_config as get_playwright_config,
    )

    return {
        "brave": get_brave_config(),
        "playwright": get_playwright_config(),
    }


# =============================================================================
# TOOL RESOLVER
# =============================================================================

class ToolResolver:
    """
    Resuelve y prepara las tools (locales + MCP) para el ChatTeamsAgent.

    Sigue el mismo patrón que ``aiagents/scraper/tool_executor.ToolResolver``:
    - Cargar tools locales (ScraperAgent wrappers + list_available_agents)
    - Conectar a MCP servers y obtener tools remotas (Brave Search, Playwright)
    - Configurar error handlers en tools MCP
    - Limpiar conexiones MCP al finalizar

    Responsabilidades:
    - Resolución de tools: ``resolve_tools()``
    - Lifecycle del MCP client: ``cleanup()``
    - Timeout en conexión MCP para evitar colgarse
    """

    def __init__(
        self,
        use_mcp: bool = True,
        custom_tools: Optional[List[BaseTool]] = None,
    ):
        """
        Args:
            use_mcp: Si cargar tools MCP (Brave, Playwright) para queries ad-hoc.
            custom_tools: Tools custom en vez de las por defecto.
        """
        self._use_mcp = use_mcp
        self._custom_tools = custom_tools
        self._mcp_client: Optional[MultiServerMCPClient] = None

    def _get_local_tools(self) -> List[BaseTool]:
        """Obtiene las tools locales (ScraperAgent wrappers)."""
        if self._custom_tools is not None:
            return list(self._custom_tools)
        return get_chat_teams_tools()

    async def resolve_tools(self) -> List[BaseTool]:
        """
        Resuelve todas las tools disponibles (locales + MCP).

        Incluye timeout de _MCP_CONNECT_TIMEOUT segundos para no colgarse
        si los MCPs no son accesibles (ej: Rancher sin port-forward activo).

        Returns:
            Lista de todas las tools listas para usar.
        """
        all_tools = self._get_local_tools()

        if self._use_mcp:
            try:
                mcp_configs = get_mcp_configs()
                self._mcp_client = MultiServerMCPClient(mcp_configs)

                # Timeout para evitar colgarse si MCPs no están accesibles
                mcp_tools = await asyncio.wait_for(
                    self._mcp_client.get_tools(),
                    timeout=_MCP_CONNECT_TIMEOUT,
                )

                # Configurar manejo de errores en tools MCP
                for t in mcp_tools:
                    t.handle_tool_error = _tool_error_handler

                all_tools.extend(mcp_tools)
                logger.info(
                    f"MCP tools loaded for ChatTeams: {[t.name for t in mcp_tools]}"
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"MCP connection timed out after {_MCP_CONNECT_TIMEOUT}s. "
                    f"MCPs not reachable — agent will work with local tools only. "
                    f"Check docker-compose up or Rancher port-forward."
                )
            except Exception as e:
                logger.warning(
                    f"Error cargando MCP tools: {e}. Continuando solo con tools locales."
                )

        local_count = len(self._get_local_tools())
        mcp_count = len(all_tools) - local_count
        logger.info(
            f"ChatTeams ToolResolver: {local_count} local + {mcp_count} MCP = "
            f"{len(all_tools)} total tools"
        )
        return all_tools

    async def cleanup(self) -> None:
        """Libera recursos (cierra MCP client)."""
        if self._mcp_client:
            try:
                if hasattr(self._mcp_client, "close"):
                    await self._mcp_client.close()
                logger.info("ChatTeams MCP client cleaned up")
            except Exception as e:
                logger.debug(f"Error cerrando MCP client: {e}")
            finally:
                self._mcp_client = None

    @property
    def mcp_client(self) -> Optional[MultiServerMCPClient]:
        """Acceso al MCP client (para inspección/testing)."""
        return self._mcp_client