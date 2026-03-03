"""
Test 1.3.7: Verificar memoria multi-turn del ScraperAgent.

Valida que llamar a agent.run() dos veces con el mismo thread_id
acumula contexto (el agente "recuerda" la primera llamada).

Documentación oficial consultada:
- https://langchain-ai.github.io/langgraph/how-tos/persistence/
- Patrón: checkpointer=InMemorySaver() + {"configurable": {"thread_id": "X"}}
- Mismo thread_id entre invocaciones → el agente mantiene historial

Ejecución: python scripts/test_memory_multiturn.py
Requiere: Docker MCPs running (start.sh) + .env con API keys
"""

import asyncio
import json
import sys
sys.path.insert(0, '.')

from aifoundry.app.core.aiagents.scraper.agent import ScraperAgent
from aifoundry.app.utils.country import get_country_info


async def test_multiturn_memory():
    """
    Test multi-turn: dos queries al mismo agente, verificando que
    la segunda respuesta puede referenciar información de la primera.
    """
    # Cargar config de electricidad (simple y rápido)
    with open("aifoundry/app/core/aiagents/scraper/electricity/config.json") as f:
        config_file = json.load(f)

    country = "ES"
    country_info = get_country_info(country)
    language = config_file["countries"][country]["language"]

    # ─── PRIMERA QUERY ───────────────────────────────────────────
    config_turn1 = {
        "product": config_file["product"],
        "provider": "Iberdrola",
        "country_code": country,
        "language": language,
        "query": "precio luz Iberdrola España febrero 2026 tarifa regulada PVPC",
        "freshness": config_file.get("freshness", "pw"),
    }

    # ─── SEGUNDA QUERY (referencia la primera) ───────────────────
    config_turn2 = {
        "product": config_file["product"],
        "provider": "Iberdrola",
        "country_code": country,
        "language": language,
        "query": (
            "Basándote en la información que ya encontraste sobre Iberdrola, "
            "¿cuál es la tarifa más barata que encontraste? Resume en 2 líneas."
        ),
        "freshness": config_file.get("freshness", "pw"),
    }

    print("=" * 60)
    print("TEST 1.3.7: Memoria Multi-Turn del ScraperAgent")
    print("=" * 60)

    async with ScraperAgent(
        use_mcp=True,
        verbose=True,
        use_memory=True,       # ← CLAVE: memoria activada
        structured_output=False,
    ) as agent:

        thread_id = agent.thread_id
        print(f"\n🧵 Thread ID: {thread_id}")

        # ── TURN 1 ──
        print(f"\n{'─' * 40}")
        print("📝 TURN 1: Búsqueda inicial de precios")
        print(f"{'─' * 40}")
        print(f"Query: {config_turn1['query']}")

        result1 = await agent.run(config_turn1)

        print(f"\n✅ Turn 1 completado")
        print(f"   Status: {result1['status']}")
        print(f"   Messages count: {result1['messages_count']}")
        print(f"   Thread ID: {result1['thread_id']}")
        print(f"   Output (primeros 300 chars): {result1['output'][:300]}...")

        # Verificar historial después de turn 1
        history1 = agent.get_history()
        print(f"\n📚 Historial después de Turn 1: {len(history1) if history1 else 0} mensajes")

        # ── TURN 2 (usa misma instancia → mismo thread_id → tiene memoria) ──
        print(f"\n{'─' * 40}")
        print("📝 TURN 2: Follow-up (debe recordar Turn 1)")
        print(f"{'─' * 40}")
        print(f"Query: {config_turn2['query']}")

        result2 = await agent.run(config_turn2)

        print(f"\n✅ Turn 2 completado")
        print(f"   Status: {result2['status']}")
        print(f"   Messages count: {result2['messages_count']}")
        print(f"   Thread ID: {result2['thread_id']}")
        print(f"   Output (primeros 500 chars): {result2['output'][:500]}...")

        # Verificar historial después de turn 2
        history2 = agent.get_history()
        print(f"\n📚 Historial después de Turn 2: {len(history2) if history2 else 0} mensajes")

        # ── VALIDACIONES ──
        print(f"\n{'═' * 60}")
        print("🔍 VALIDACIONES")
        print(f"{'═' * 60}")

        checks = []

        # Check 1: Mismo thread_id en ambos turns
        same_thread = result1["thread_id"] == result2["thread_id"]
        checks.append(("Mismo thread_id en ambos turns", same_thread))

        # Check 2: Historial crece entre turns
        h1_len = len(history1) if history1 else 0
        h2_len = len(history2) if history2 else 0
        history_grows = h2_len > h1_len
        checks.append((f"Historial crece ({h1_len} → {h2_len} mensajes)", history_grows))

        # Check 3: Turn 2 tiene más mensajes acumulados que Turn 1
        more_msgs = result2["messages_count"] > result1["messages_count"]
        checks.append((
            f"Turn 2 acumula más mensajes ({result1['messages_count']} → {result2['messages_count']})",
            more_msgs,
        ))

        # Check 4: Ambos turns exitosos
        both_success = result1["status"] == "success" and result2["status"] == "success"
        checks.append(("Ambos turns exitosos", both_success))

        all_passed = True
        for desc, passed in checks:
            icon = "✅" if passed else "❌"
            print(f"  {icon} {desc}")
            if not passed:
                all_passed = False

        print(f"\n{'═' * 60}")
        if all_passed:
            print("🎉 TODOS LOS CHECKS PASARON — Memoria multi-turn funciona correctamente")
        else:
            print("⚠️  ALGUNOS CHECKS FALLARON — Revisar implementación del checkpointer")
        print(f"{'═' * 60}")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_multiturn_memory())
    sys.exit(0 if success else 1)