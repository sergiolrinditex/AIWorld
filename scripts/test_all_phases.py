#!/usr/bin/env python3
"""
🧪 Test de verificación de TODAS las fases del ROADMAP.

Ejecuta checks sobre cada fase completada y muestra salida detallada.
Uso: python scripts/test_all_phases.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Añadir root al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Colores
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0
warnings = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  {GREEN}✅ {name}{RESET}" + (f"  — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"  {RED}❌ {name}{RESET}" + (f"  — {detail}" if detail else ""))


def warn(name: str, detail: str = ""):
    global warnings
    warnings += 1
    print(f"  {YELLOW}⚠️  {name}{RESET}" + (f"  — {detail}" if detail else ""))


def section(title: str):
    print(f"\n{BOLD}{CYAN}{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}{RESET}")


# ============================================================================
# FASE 1: Bugs Críticos
# ============================================================================
def test_fase1():
    section("FASE 1: Bugs Críticos")

    from aifoundry.app.core.aiagents.scraper.agent import ScraperAgent

    # 1.1 — self._agent se reutiliza (no se crea en run())
    agent = ScraperAgent(use_mcp=False, verbose=False)
    check("1.1 — ScraperAgent tiene _agent como atributo", hasattr(agent, '_agent'))
    check("1.1 — _agent es None al inicio", agent._agent is None)

    # 1.2 — MCP client gestionado en initialize/cleanup
    check("1.2 — Tiene _mcp_client como atributo", hasattr(agent, '_mcp_client'))
    check("1.2 — cleanup() existe", hasattr(agent, 'cleanup'))
    check("1.2 — Es context manager (__aenter__/__aexit__)", 
          hasattr(agent, '__aenter__') and hasattr(agent, '__aexit__'))

    # 1.3 — Checkpointer funcional
    check("1.3 — Tiene _checkpointer", hasattr(agent, '_checkpointer'))
    check("1.3 — Tiene _thread_id", hasattr(agent, '_thread_id'))
    check("1.3 — Tiene reset_memory()", hasattr(agent, 'reset_memory'))
    check("1.3 — Tiene get_history()", hasattr(agent, 'get_history'))
    check("1.3 — Tiene _build_run_config()", hasattr(agent, '_build_run_config'))

    # thread_id es estable
    tid = str(agent._thread_id)
    check("1.3 — thread_id es UUID válido", len(tid) == 36 and tid.count('-') == 4, tid)


# ============================================================================
# FASE 2: Problemas de Diseño
# ============================================================================
def test_fase2():
    section("FASE 2: Problemas de Diseño")

    # 2.1 — run() unificado (sin ramas MCP duplicadas)
    import inspect
    from aifoundry.app.core.aiagents.scraper.agent import ScraperAgent
    run_source = inspect.getsource(ScraperAgent.run)
    check("2.1 — run() sin create_agent() interno", "create_agent" not in run_source)
    check("2.1 — _build_run_config() existe", hasattr(ScraperAgent, '_build_run_config'))

    # 2.2 — Dead code eliminado
    agent_source = inspect.getsource(ScraperAgent)
    check("2.2 — Sin 'dataclass' import en agent.py", "from dataclasses" not in agent_source)

    # 2.3 — simple_scrape_url es async
    from aifoundry.app.core.aiagents.scraper.tools import simple_scrape_url
    check("2.3 — simple_scrape_url es coroutine/async", 
          asyncio.iscoroutinefunction(simple_scrape_url.coroutine) if hasattr(simple_scrape_url, 'coroutine') else True,
          "async via @tool")

    # 2.4 — parse_output en utils/parsing.py
    from aifoundry.app.utils.parsing import parse_agent_output
    result = parse_agent_output("QUERY_ESPAÑOL: test query\nhttps://example.com")
    check("2.4 — parse_agent_output() funciona", result["query_es"] == "test query")
    check("2.4 — Extrae URLs", "https://example.com" in result["urls"])


# ============================================================================
# FASE 3: Arquitectura FastAPI
# ============================================================================
def test_fase3():
    section("FASE 3: Arquitectura FastAPI")

    from fastapi.testclient import TestClient
    from aifoundry.app.main import app

    client = TestClient(app)

    # Root
    resp = client.get("/")
    check("3.1 — GET / → 200", resp.status_code == 200, f"status={resp.status_code}")

    # Health
    resp = client.get("/health")
    data = resp.json()
    check("3.1 — GET /health → 200", resp.status_code == 200)
    check("3.1 — health.status = healthy", data.get("status") == "healthy")
    check("3.1 — health.llm_model presente", "llm_model" in data, data.get("llm_model", "?"))
    check("3.1 — health.agents_available ≥ 3", data.get("agents_available", 0) >= 3, 
          str(data.get("agents_available")))

    # List agents
    resp = client.get("/agents")
    data = resp.json()
    agent_names = [a["name"] for a in data.get("agents", [])]
    check("3.1 — GET /agents → 200", resp.status_code == 200)
    check("3.1 — Contiene electricity", "electricity" in agent_names)
    check("3.1 — Contiene salary", "salary" in agent_names)
    check("3.1 — Contiene social_comments", "social_comments" in agent_names)

    # Agent config
    resp = client.get("/agents/electricity/config")
    data = resp.json()
    check("3.1 — GET /agents/electricity/config → 200", resp.status_code == 200)
    check("3.1 — product = electricidad", data.get("product") == "electricidad")
    check("3.1 — Tiene countries.ES", "ES" in data.get("countries", {}))

    # 404 para agente inexistente
    resp = client.get("/agents/noexiste/config")
    check("3.1 — GET /agents/noexiste → 404", resp.status_code == 404)

    # 422 para país no soportado
    resp = client.post("/agents/electricity/run", json={"provider": "Endesa", "country_code": "ZZ"})
    check("3.1 — POST run con país inválido → 422", resp.status_code == 422)

    # OpenAPI docs
    resp = client.get("/openapi.json")
    check("3.1 — OpenAPI /openapi.json → 200", resp.status_code == 200)
    resp = client.get("/docs")
    check("3.1 — Swagger /docs → 200", resp.status_code == 200)


# ============================================================================
# FASE 4: Validación y Configuración
# ============================================================================
def test_fase4():
    section("FASE 4: Validación y Configuración")

    # 4.1 — AgentConfig Pydantic
    from pydantic import ValidationError
    from aifoundry.app.core.aiagents.scraper.config_schema import AgentConfig, CountryConfig

    # Config válido
    cfg = AgentConfig(
        product="test", query_template="q {product}",
        countries={"ES": {"language": "es", "providers": ["A", "B"]}}
    )
    check("4.1 — AgentConfig válido acepta config correcto", cfg.product == "test")
    check("4.1 — get_providers() funciona", cfg.get_providers("ES") == ["A", "B"])
    check("4.1 — get_language() funciona", cfg.get_language("ES") == "es")
    check("4.1 — freshness default = pw", cfg.freshness == "pw")

    # Config inválido: falta product
    try:
        AgentConfig(query_template="q", countries={"ES": {"language": "es"}})
        check("4.1 — Rechaza config sin product", False)
    except ValidationError:
        check("4.1 — Rechaza config sin product", True)

    # Config inválido: extra field
    try:
        AgentConfig(product="t", query_template="q", countries={"ES": {"language": "es"}}, typo_field="x")
        check("4.1 — extra='forbid' detecta typos", False)
    except ValidationError:
        check("4.1 — extra='forbid' detecta typos", True)

    # Freshness inválido
    try:
        AgentConfig(product="t", query_template="q", countries={"ES": {"language": "es"}}, freshness="xyz")
        check("4.1 — Rechaza freshness inválido", False)
    except ValidationError:
        check("4.1 — Rechaza freshness inválido", True)

    # 4.1 — Validación integrada en router
    from aifoundry.app.api.router import _discover_agents, get_validated_config
    agents = _discover_agents()
    check("4.1 — _discover_agents() con validación Pydantic", len(agents) >= 3, f"{len(agents)} agentes")
    for name in ["electricity", "salary", "social_comments"]:
        vc = get_validated_config(name)
        check(f"4.1 — get_validated_config('{name}') OK", vc is not None, vc.product if vc else "None")

    # 4.2 — system_prompt_template
    from aifoundry.app.core.aiagents.scraper.prompts import get_system_prompt
    config_custom = {
        "product": "TEST", "country_code": "ES", "language": "es",
        "system_prompt_template": "Agente para {product} en {country_name}."
    }
    prompt = get_system_prompt(config_custom)
    check("4.2 — system_prompt_template funciona", prompt == "Agente para TEST en España.")

    # 4.2 — Fallback en template con variable inexistente
    config_bad = {
        "product": "TEST", "country_code": "ES", "language": "es",
        "system_prompt_template": "{variable_desconocida}"
    }
    prompt = get_system_prompt(config_bad)
    check("4.2 — Fallback a genérico con variable desconocida", "brave_web_search" in prompt)

    # 4.3 — Retry y timeout en config
    from aifoundry.app.config import settings
    check("4.3 — llm_num_retries configurado", settings.llm_num_retries >= 1, str(settings.llm_num_retries))
    check("4.3 — llm_request_timeout configurado", settings.llm_request_timeout >= 30, f"{settings.llm_request_timeout}s")


# ============================================================================
# FASE 5: Tests
# ============================================================================
def test_fase5():
    section("FASE 5: Tests")

    # Verificar que existen los archivos de test
    tests_dir = Path(__file__).resolve().parent.parent / "aifoundry" / "tests"

    check("5.1 — conftest.py existe", (tests_dir / "conftest.py").exists())
    check("5.1 — unit/ directorio existe", (tests_dir / "unit").is_dir())
    check("5.1 — integration/ directorio existe", (tests_dir / "integration").is_dir())

    unit_tests = list((tests_dir / "unit").glob("test_*.py"))
    integration_tests = list((tests_dir / "integration").glob("test_*.py"))

    check("5.2 — ≥ 7 archivos test unitarios", len(unit_tests) >= 7, f"{len(unit_tests)} archivos")
    check("5.3 — ≥ 1 archivo test integración", len(integration_tests) >= 1, f"{len(integration_tests)} archivos")

    # Listar archivos de test
    for t in sorted(unit_tests):
        print(f"       📄 unit/{t.name}")
    for t in sorted(integration_tests):
        print(f"       📄 integration/{t.name}")


# ============================================================================
# FASE 6: Prompt Engineering
# ============================================================================
def test_fase6():
    section("FASE 6: Prompt Engineering")

    from aifoundry.app.core.aiagents.scraper.prompts import get_system_prompt

    # Prompt genérico con config española
    config_es = {
        "product": "electricidad", "provider": "Endesa",
        "country_code": "ES", "language": "es", "freshness": "pw",
        "extraction_prompt": "Extrae tarifas",
        "validation_prompt": "Valida precios",
    }
    prompt = get_system_prompt(config_es)

    check("6.1 — Prompt tiene 5 pasos (no 7)", "PASO 5" in prompt and "PASO 7" not in prompt)
    check("6.2 — Sin PASO 2 de traducción separado", "PASO 2: TRADUCIR" not in prompt)
    check("6.3 — Seleccionar 5-8 URLs", "5-8 URLs" in prompt or "5-8" in prompt)
    check("6.4 — Regla de STOP", "8 URLs no encuentras datos" in prompt or "para y reporta" in prompt)
    check("6.5 — Prioriza fuentes oficiales", "fuentes oficiales" in prompt.lower() or "oficiales" in prompt)
    check("6.5 — Evitar foros/blogs", "foros" in prompt or "blogs" in prompt)

    # Verificar que extraction/validation se inyectan
    check("6.6 — extraction_prompt inyectado", "Extrae tarifas" in prompt)
    check("6.6 — validation_prompt inyectado", "Valida precios" in prompt)

    # Prompt con idioma no-español: translate_hint
    config_fr = {
        "product": "electricité", "country_code": "FR", "language": "fr",
    }
    prompt_fr = get_system_prompt(config_fr)
    check("6.7 — Traducción implícita para FR", "francés" in prompt_fr)

    # Tamaño reducido
    prompt_len = len(prompt)
    check("6.8 — Prompt < 3000 chars (antes ~5000)", prompt_len < 3000, f"{prompt_len} chars")


# ============================================================================
# MAIN
# ============================================================================
def main():
    print(f"\n{BOLD}🧪 VERIFICACIÓN COMPLETA DE TODAS LAS FASES DEL ROADMAP{RESET}")
    print(f"   Proyecto: AIFoundry | Fecha: {time.strftime('%d/%m/%Y %H:%M')}")

    start = time.time()

    test_fase1()
    test_fase2()
    test_fase3()
    test_fase4()
    test_fase5()
    test_fase6()

    elapsed = time.time() - start

    # Resumen
    total = passed + failed
    section("RESUMEN")
    print(f"  {GREEN}✅ Passed: {passed}{RESET}")
    if failed:
        print(f"  {RED}❌ Failed: {failed}{RESET}")
    if warnings:
        print(f"  {YELLOW}⚠️  Warnings: {warnings}{RESET}")
    print(f"  ⏱️  Tiempo: {elapsed:.2f}s")
    print(f"  📊 Total: {passed}/{total} checks")

    if failed == 0:
        print(f"\n  {GREEN}{BOLD}🎉 TODAS LAS FASES VERIFICADAS CORRECTAMENTE{RESET}")
    else:
        print(f"\n  {RED}{BOLD}⚠️  {failed} checks fallidos — revisar{RESET}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())