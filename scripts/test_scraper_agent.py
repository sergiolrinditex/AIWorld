"""
Test del ScraperAgent.

Prueba que el agente reformula la query incluyendo país y fecha.

Uso:
    source .venv/bin/activate && python scripts/test_scraper_agent.py
"""

import asyncio
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from aifoundry.app.core.aiagents import ScraperAgent


async def main():
    """Test del ScraperAgent con reformulación de query."""
    
    print("\n" + "="*60)
    print("TEST: ScraperAgent - Reformulación de Query")
    print("="*60 + "\n")
    
    # Crear agente
    agent = ScraperAgent()
    print("✅ Agente creado\n")
    
    # Test: Query simple que debe reformularse
    query = "quiero saber el precio de la luz"
    country = "ES"
    
    print(f"🔍 Query original: {query}")
    print(f"🌍 País: {country}")
    print(f"\nEsperamos que el agente reformule a algo como:")
    print(f"   'precio de luz en España en 13 enero 2026'\n")
    
    result = await agent.run(query, country_code=country)
    
    print("\n" + "-"*40)
    print("RESULTADO:")
    print("-"*40)
    print(f"Status: {result['status']}")
    print(f"Messages: {result.get('messages_count', 'N/A')}")
    print(f"\nOutput:\n{result['output']}")
    
    if result["status"] == "error":
        print(f"\n❌ Error: {result['output']}")
    else:
        print("\n✅ Test completado")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())