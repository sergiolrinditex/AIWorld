"""
Tools para el ChatTeamsAgent.

Wrappea los ScraperAgents existentes como tools que el Deep Agent puede invocar.
Cada tool delega a un ScraperAgent con la config de dominio correspondiente.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from aifoundry.app.core.aiagents.scraper.agent import ScraperAgent

logger = logging.getLogger(__name__)

# Ruta base a los configs de dominio del ScraperAgent
_SCRAPER_CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "aiagents" / "scraper"


def _load_domain_config(domain: str) -> dict:
    """Carga un config.json de dominio del ScraperAgent."""
    config_path = _SCRAPER_CONFIG_DIR / domain / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
        return json.load(f)


def _add_date_context(query: str) -> str:
    """
    Añade la fecha actual a la query si no contiene ya una referencia temporal.

    Esto asegura que los ScraperAgents busquen datos actualizados.
    Si el usuario ya mencionó una fecha/mes/año, no se duplica.
    """
    now = datetime.now(timezone.utc)
    months_es = [
        "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    date_str = f"{months_es[now.month]} {now.year}"
    date_iso = now.strftime("%Y-%m-%d")

    # Heurística: si la query ya menciona un año (4 dígitos tipo 202x/203x) no añadir fecha
    if re.search(r"\b20[2-3]\d\b", query):
        return query

    return f"{query} (fecha actual: {date_str}, {date_iso})"


# Timeout para ejecución de ScraperAgents (segundos)
_SCRAPER_TIMEOUT = 120


async def _run_scraper(
    domain: str,
    query: str,
    provider: Optional[str] = None,
    country_code: Optional[str] = None,
) -> str:
    """
    Ejecuta un ScraperAgent con un dominio específico.

    Pasa provider y country_code como campos separados del config
    (igual que hace test_electricity_agent.py) para que el system prompt
    del ScraperAgent los use correctamente sin duplicar en la query.

    Incluye timeout de _SCRAPER_TIMEOUT segundos para evitar que se cuelgue
    si los MCPs no son accesibles (ej: Rancher sin port-forward).

    Args:
        domain: Nombre del dominio (electricity, salary, social_comments)
        query: Query de búsqueda en lenguaje natural (sin duplicar provider/country)
        provider: Proveedor/empresa (campo separado para el ScraperAgent config)
        country_code: Código ISO del país (campo separado para el ScraperAgent config)

    Returns:
        Output del agente como string
    """
    try:
        # Siempre incluir fecha actual en la query
        dated_query = _add_date_context(query)

        # Cargar config de dominio y añadir la query
        domain_config = _load_domain_config(domain)
        domain_config["query"] = dated_query
        thread_id = f"chat-teams-{domain}-{id(query)}"
        domain_config["thread_id"] = thread_id

        # Pasar provider y country_code como campos separados del config
        # El ScraperAgent system prompt los usa para enfocar la búsqueda
        if provider:
            domain_config["provider"] = provider
        if country_code:
            domain_config["country_code"] = country_code
            # Derivar language del config.json countries si está disponible
            countries = domain_config.get("countries", {})
            if country_code in countries:
                domain_config["language"] = countries[country_code].get("language", "es")

        logger.info(
            f"ScraperAgent ({domain}) query: {dated_query}"
            f"{f', provider={provider}' if provider else ''}"
            f"{f', country={country_code}' if country_code else ''}"
        )

        async def _execute():
            async with ScraperAgent() as agent:
                result = await agent.run(domain_config, max_retries=2)
                return result.get("output", "Sin resultado")

        output = await asyncio.wait_for(_execute(), timeout=_SCRAPER_TIMEOUT)
        return str(output)
    except asyncio.TimeoutError:
        logger.error(f"ScraperAgent ({domain}) timed out after {_SCRAPER_TIMEOUT}s")
        return (
            f"El agente de {domain} tardó demasiado (>{_SCRAPER_TIMEOUT}s). "
            f"Posible causa: MCPs no accesibles. Verifica que los servicios MCP "
            f"están corriendo (docker-compose up o port-forward de Rancher)."
        )
    except Exception as e:
        logger.error(f"ScraperAgent ({domain}) failed: {e}")
        return f"Error ejecutando agente de {domain}: {str(e)[:500]}"


# =============================================================================
# TOOLS — Cada una wrappea un ScraperAgent con su config de dominio
# =============================================================================


@tool
async def search_electricity(
    query: str,
    country_code: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """
    Busca información sobre precios de electricidad y tarifas energéticas.

    Usa esta herramienta cuando el usuario pregunte sobre:
    - Precios de luz/electricidad en un país
    - Tarifas de proveedores energéticos (Endesa, Iberdrola, EDF, etc.)
    - Comparativas de precios de energía
    - Cambios regulatorios en el sector eléctrico

    IMPORTANTE: NO incluyas fechas ni años en la query. El sistema añade
    automáticamente la fecha actual. Pasa solo el tema de búsqueda.

    Args:
        query: Consulta de búsqueda sobre electricidad SIN fechas ni años.
               Ejemplo correcto: "precio electricidad Endesa España"
               Ejemplo INCORRECTO: "precio electricidad Endesa España 2024"
        country_code: Código de país ISO (ej: "ES", "FR", "DE"). Opcional.
        provider: Nombre del proveedor eléctrico. Opcional.

    Returns:
        Información encontrada sobre precios de electricidad.
    """
    return await _run_scraper(
        "electricity",
        query,
        provider=provider,
        country_code=country_code,
    )


@tool
async def search_salary(
    query: str,
    country_code: Optional[str] = None,
    company: Optional[str] = None,
) -> str:
    """
    Busca información sobre salarios y compensación en la industria retail/moda.

    Usa esta herramienta cuando el usuario pregunte sobre:
    - Salarios en empresas de moda (Zara, H&M, Primark, etc.)
    - Compensación en retail por país
    - Comparativas salariales del sector
    - Beneficios y condiciones laborales

    IMPORTANTE: NO incluyas fechas ni años en la query. El sistema añade
    automáticamente la fecha actual. Pasa solo el tema de búsqueda.

    Args:
        query: Consulta de búsqueda sobre salarios SIN fechas ni años.
               Ejemplo correcto: "salario medio dependiente Zara España"
               Ejemplo INCORRECTO: "salario medio dependiente Zara España 2024"
        country_code: Código de país ISO (ej: "ES", "UK", "US"). Opcional.
        company: Nombre de la empresa. Opcional.

    Returns:
        Información encontrada sobre salarios y compensación.
    """
    return await _run_scraper(
        "salary",
        query,
        provider=company,
        country_code=country_code,
    )


@tool
async def search_social_comments(
    query: str,
    person_name: Optional[str] = None,
    social_network: Optional[str] = None,
) -> str:
    """
    Busca comentarios y menciones en redes sociales.

    Usa esta herramienta cuando el usuario pregunte sobre:
    - Menciones de personas en redes sociales
    - Comentarios públicos sobre alguien en Instagram, X/Twitter, LinkedIn, etc.
    - Reputación online de una persona
    - Sentimiento en redes sociales

    IMPORTANTE: NO incluyas fechas ni años en la query. El sistema añade
    automáticamente la fecha actual. Pasa solo el tema de búsqueda.

    Args:
        query: Consulta de búsqueda SIN fechas ni años.
               Ejemplo correcto: "comentarios sobre Pablo Isla en LinkedIn"
               Ejemplo INCORRECTO: "comentarios sobre Pablo Isla en LinkedIn 2024"
        person_name: Nombre de la persona a buscar. Opcional.
        social_network: Red social específica (Instagram, X, LinkedIn, TikTok, etc.). Opcional.

    Returns:
        Comentarios y menciones encontradas en redes sociales.
    """
    return await _run_scraper(
        "social_comments",
        query,
        provider=person_name,
    )


@tool
async def list_available_agents() -> str:
    """
    Lista los agentes de scraping disponibles y sus configuraciones.

    Usa esta herramienta cuando el usuario pregunte qué puedes hacer,
    qué agentes hay disponibles, o qué dominios soportas.

    Returns:
        Descripción de los agentes disponibles con sus países y proveedores.
    """
    result_parts = ["## Agentes disponibles\n"]

    for domain in ["electricity", "salary", "social_comments"]:
        try:
            config = _load_domain_config(domain)
            result_parts.append(f"### 🔹 {domain}")
            result_parts.append(f"**Producto:** {config.get('product', 'N/A')}")
            result_parts.append(f"**Frescura:** {config.get('freshness', 'N/A')}")

            providers = config.get("providers_by_country", {})
            if providers:
                countries = list(providers.keys())
                result_parts.append(f"**Países:** {', '.join(countries)}")
                for country in countries[:3]:
                    provs = providers[country]
                    result_parts.append(f"  - {country}: {', '.join(provs)}")
                if len(countries) > 3:
                    result_parts.append(f"  - ... y {len(countries) - 3} países más")

            networks = config.get("social_networks", [])
            if networks:
                result_parts.append(f"**Redes sociales:** {', '.join(networks)}")

            result_parts.append("")
        except Exception as e:
            result_parts.append(f"### ⚠️ {domain}: Error cargando config — {e}\n")

    return "\n".join(result_parts)


def get_chat_teams_tools() -> list:
    """
    Retorna las tools locales para el ChatTeamsAgent.

    Solo definiciones de tools — la resolución MCP se hace en tool_executor.py
    (mismo patrón que aiagents/scraper con tools.py + tool_executor.py).
    """
    return [
        search_electricity,
        search_salary,
        search_social_comments,
        list_available_agents,
    ]
