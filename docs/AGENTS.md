# 🤖 Agentes de AIWorld — Guía Completa

> Documentación de los dos niveles de agentes: **ScraperAgent** (AI Agent) y **ChatTeamsAgent** (Agentic AI / Deep Agent).

**Versión**: 2.0.0
**Última actualización**: Abril 2026

---

## 📖 Índice

1. [Visión General](#visión-general)
2. [ScraperAgent (ReAct)](#scraperagent-react)
3. [ChatTeamsAgent (Deep Agent)](#chatteamsagent-deep-agent)
4. [Herramientas (Tools)](#herramientas-tools)
5. [Configuración de Dominios](#configuración-de-dominios)
6. [Crear un Nuevo Dominio](#crear-un-nuevo-dominio)
7. [Memoria y Estado](#memoria-y-estado)
8. [Troubleshooting](#troubleshooting)

---

## Visión General

AIWorld implementa un sistema de agentes en **dos capas**:

```
                    ┌─────────────────────────────┐
                    │     ChatTeamsAgent           │
                    │     (Deep Agent)             │
                    │                              │
                    │  Orquestador conversacional   │
                    │  deepagents.create_deep_agent │
                    └──────┬──────┬──────┬─────────┘
                           │      │      │
              ┌────────────┘      │      └────────────┐
              ▼                   ▼                    ▼
    ┌──────────────┐   ┌──────────────┐   ┌────────────────┐
    │ ScraperAgent │   │ ScraperAgent │   │  ScraperAgent  │
    │ (electricity)│   │ (salary)     │   │  (social_      │
    │              │   │              │   │   comments)    │
    └──────────────┘   └──────────────┘   └────────────────┘
           │                  │                    │
           ▼                  ▼                    ▼
    ┌─────────────────────────────────────────────────────┐
    │        MCP Tools + Local Tools                       │
    │  Brave Search · Playwright · simple_scrape_url       │
    └─────────────────────────────────────────────────────┘
```

| Capa | Agente | Librería | Patrón | Rol |
|------|--------|----------|--------|-----|
| **Agentic AI** | `ChatTeamsAgent` | `deepagents` | Deep Agent | Orquestador conversacional |
| **AI Agent** | `ScraperAgent` | `langchain.agents` | ReAct | Agente especializado de scraping |

---

## ScraperAgent (ReAct)

### ¿Qué es?

Un agente **ReAct** (Reasoning + Acting) genérico para scraping web. Un único agente configurable por dominio mediante archivos `config.json`.

**Archivo**: `aifoundry/app/core/aiagents/scraper/agent.py`

### Arquitectura

```python
from langchain.agents import create_agent

agent = create_agent(
    model=ChatOpenAI(via LiteLLM proxy),
    tools=[brave_search, playwright, simple_scrape_url],
    prompt=dynamic_system_prompt(config),
)
```

### Parámetros del Constructor

```python
ScraperAgent(
    agent_name: str,            # Nombre del agente (ej: "electricity")
    config: AgentConfig,        # Configuración del dominio
    response_model: type[BaseModel] | None,  # Modelo Pydantic de respuesta
    thread_id: str | None,      # ID de conversación para memoria
)
```

### Flujo de Ejecución

1. **Recibe query** del usuario (ej: "precio luz España")
2. **Genera system prompt** dinámico desde `config.json`
3. **Razona** (ReAct) qué herramientas usar
4. **Busca** con Brave Search → obtiene URLs relevantes
5. **Extrae** contenido con Playwright o `simple_scrape_url`
6. **Valida** y estructura la respuesta con `response_model`
7. **Reintenta** automáticamente ante errores de red (retry logic)

### Structured Output

El ScraperAgent soporta **structured output nativo** (preferido):

```python
# El agente devuelve directamente un modelo Pydantic tipado
result = await agent.run(query="precio luz España", country="ES")
# result es una instancia del response_model definido en config.json
```

El mecanismo usa `response_format` del LLM para forzar output JSON que se valida contra el Pydantic model.

### Prompts Dinámicos

El system prompt se genera dinámicamente desde `config.json`:

```python
# aifoundry/app/core/aiagents/scraper/prompts.py
def get_system_prompt(config: AgentConfig) -> str:
    # Soporta custom system_prompt_template con variables:
    # {product}, {query_template}, {countries}, etc.
```

Si el `config.json` incluye `system_prompt_template`, se usa como template con variables interpoladas. Si no, se genera un prompt por defecto basado en los campos del config.

---

## ChatTeamsAgent (Deep Agent)

### ¿Qué es?

Un agente conversacional de alto nivel que usa la librería [`deepagents`](https://docs.langchain.com/oss/python/deepagents/overview) de LangChain — el approach "batteries-included" para agentes complejos.

**Archivo**: `aifoundry/app/core/agenticai/deepagents/chat_teams/agent.py`

### ¿Por qué deepagents?

Según la [documentación oficial de LangChain](https://docs.langchain.com/oss/python/deepagents/overview):

> "deepagents es una librería standalone construida sobre los building blocks de LangChain. Usa el runtime de LangGraph para ejecución durable, streaming, human-in-the-loop y otras features."

Capacidades que usamos:
- **Planning y task decomposition** (via `write_todos` tool built-in)
- **Context management** (file system tools: `ls`, `read_file`, `write_file`, `edit_file`)
- **Subagent spawning** (via `task` tool built-in)
- **Long-term memory** (via LangGraph's Memory Store)
- **Streaming** (via `astream_events` v2)

### Arquitectura

```python
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=settings.litellm_model,
    base_url=settings.litellm_base_url,
    api_key=settings.litellm_api_key,
)

agent = create_deep_agent(
    tools=[search_electricity, search_salary, search_social_comments, list_available_agents, ...mcp_tools],
    system_prompt=SYSTEM_PROMPT,
)
```

### Singleton Pattern

El ChatTeamsAgent es un **singleton con lazy initialization**:

```python
class ChatTeamsAgent:
    _instance = None
    _agent = None

    async def _ensure_agent(self):
        """Lazy init: crea el agente solo cuando se necesita por primera vez."""
        if self._agent is None:
            self._agent = create_deep_agent(...)
```

### Tools del ChatTeamsAgent

El agente tiene acceso a:

| Tool | Tipo | Descripción |
|------|------|-------------|
| `search_electricity` | Local (wrapper) | Busca precios de electricidad via ScraperAgent |
| `search_salary` | Local (wrapper) | Busca salarios via ScraperAgent |
| `search_social_comments` | Local (wrapper) | Busca comentarios sociales via ScraperAgent |
| `list_available_agents` | Local | Lista agentes/dominios disponibles |
| `brave_web_search` | MCP | Búsqueda web directa via Brave Search |
| `playwright_*` | MCP | Herramientas de navegación web (navigate, click, screenshot, etc.) |

### Streaming (SSE)

El ChatTeamsAgent usa `astream_events` v2 de LangGraph para generar eventos en tiempo real:

```python
async def chat(self, message: str, thread_id: str) -> AsyncIterator[ChatEvent]:
    async for event in self._agent.astream_events(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": thread_id}},
        version="v2",
    ):
        yield self._process_event(event)
```

Tipos de evento SSE:

| Evento | Descripción |
|--------|-------------|
| `thinking` | El agente está razonando (tokens de pensamiento) |
| `tool_start` | Inicio de llamada a una herramienta |
| `tool_end` | Resultado de una herramienta |
| `token` | Token de respuesta final |
| `end` | Fin del stream |
| `error` | Error durante la ejecución |

### Memory Multi-Turn

```python
# Cada conversación se identifica por thread_id
config = {"configurable": {"thread_id": "user-session-123"}}

# El checkpointer guarda el estado entre mensajes
checkpointer = InMemorySaver()
```

El historial se persiste en memoria (por thread_id) y permite conversaciones multi-turn naturales:

```
User: "¿Cuánto cobra un dependiente de Zara en España?"
Agent: "Según los datos encontrados, el salario medio es de..."
User: "¿Y en Francia?"  ← El agente entiende el contexto previo
Agent: "En Francia, el mismo puesto tiene un salario de..."
```

---

## Herramientas (Tools)

### Tools Locales

#### `search_electricity(query, country)`

Wrapper que instancia un ScraperAgent con el dominio `electricity`:

```python
@tool
async def search_electricity(query: str, country: str = "ES") -> str:
    agent = ScraperAgent("electricity", config=load_config("electricity"), ...)
    result = await agent.run(query=query, country=country)
    return str(result)
```

#### `search_salary(query, country)`

Wrapper que instancia un ScraperAgent con el dominio `salary`.

#### `search_social_comments(query, country)`

Wrapper que instancia un ScraperAgent con el dominio `social_comments`.

#### `list_available_agents()`

Retorna la lista de agentes/dominios disponibles con su descripción.

#### `simple_scrape_url(url)`

Herramienta local de scraping simple (sin navegador) para extraer texto de URLs:

```python
@tool
async def simple_scrape_url(url: str) -> str:
    """Scrape a URL and return markdown content (max 10000 chars)."""
    # Usa asyncio.to_thread para ejecutar scraper sincrónico
    # Sugiere Playwright si falla
```

### Tools MCP

Las herramientas MCP se cargan dinámicamente via `langchain-mcp-adapters`:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async with MultiServerMCPClient(mcp_configs) as client:
    mcp_tools = client.get_tools()
```

Ver [docs/MCP.md](MCP.md) para detalles sobre los servidores MCP.

---

## Configuración de Dominios

Cada dominio se configura con un archivo `config.json`:

### Ubicación

```
aifoundry/app/core/aiagents/scraper/
├── electricity/config.json
├── salary/config.json
└── social_comments/config.json
```

### Schema del config.json

```json
{
  "product": "electricity_prices",
  "query_template": "electricity prices {country} latest tariffs domestic consumers",
  "freshness": "pw",
  "count": 10,
  "extraction_prompt": "Extract electricity price data...",
  "validation_prompt": "Validate the extracted data...",
  "countries": ["ES", "PT", "FR", "IT", "DE"],
  "system_prompt_template": "You are an expert researcher... {product} ... {countries}"
}
```

### Campos

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `product` | `str` | ✅ | Identificador del dominio |
| `query_template` | `str` | ✅ | Template de búsqueda con `{country}` |
| `freshness` | `str` | ❌ | Filtro temporal Brave Search (`pd`=día, `pw`=semana, `pm`=mes) |
| `count` | `int` | ❌ | Número máximo de resultados de búsqueda |
| `extraction_prompt` | `str` | ✅ | Prompt para extracción de datos |
| `validation_prompt` | `str` | ❌ | Prompt para validación de datos |
| `countries` | `list[str]` | ✅ | Códigos ISO de países soportados |
| `system_prompt_template` | `str` | ❌ | Template custom del system prompt |

---

## Crear un Nuevo Dominio

### Paso 1: Crear el directorio y config.json

```bash
mkdir -p aifoundry/app/core/aiagents/scraper/mi_dominio/
```

```json
// aifoundry/app/core/aiagents/scraper/mi_dominio/config.json
{
  "product": "mi_producto",
  "query_template": "búsqueda {country} mi producto datos recientes",
  "freshness": "pm",
  "count": 10,
  "extraction_prompt": "Extrae los datos relevantes de mi producto...",
  "validation_prompt": "Valida que los datos sean correctos...",
  "countries": ["ES", "FR", "IT"]
}
```

### Paso 2: (Opcional) Crear un Pydantic response_model

```python
# Si quieres structured output tipado
from pydantic import BaseModel

class MiProductoResponse(BaseModel):
    dato_1: str
    dato_2: float
    pais: str
```

### Paso 3: Añadir tool wrapper en chat_teams/tools.py

```python
# aifoundry/app/core/agenticai/deepagents/chat_teams/tools.py

@tool
async def search_mi_dominio(query: str, country: str = "ES") -> str:
    """Busca datos de mi dominio para un país específico."""
    agent = ScraperAgent(
        agent_name="mi_dominio",
        config=load_config("mi_dominio"),
        response_model=MiProductoResponse,  # opcional
    )
    result = await agent.run(query=query, country=country)
    return str(result)
```

### Paso 4: Registrar en el ChatTeamsAgent

Añadir la nueva tool a la lista de tools en `chat_teams/tools.py` → función `get_all_tools()`.

### Paso 5: Actualizar el system prompt

Editar `chat_teams/prompts.py` para que el ChatTeamsAgent sepa que existe el nuevo dominio y cuándo usarlo.

### Paso 6: Probar

```bash
# Test directo del agente
python -c "
import asyncio
from aifoundry.app.core.aiagents.scraper.agent import ScraperAgent
# ... test
"

# O via API
curl -X POST http://localhost:8000/api/agents/mi_dominio/run \
  -H 'Content-Type: application/json' \
  -d '{"query": "datos mi producto España", "country": "ES"}'
```

---

## Memoria y Estado

### ScraperAgent

- **Checkpointer**: `InMemorySaver` de LangGraph
- **Scope**: por `thread_id` (sesión de conversación)
- **Uso**: mantener contexto durante la ejecución de un agente (ReAct steps)
- **Persistencia**: en memoria (se pierde al reiniciar)

### ChatTeamsAgent

- **Checkpointer**: `InMemorySaver` de LangGraph
- **Scope**: por `thread_id` (sesión de usuario)
- **Uso**: conversaciones multi-turn con contexto persistente
- **Persistencia**: en memoria (se pierde al reiniciar)

> **Roadmap**: migrar a LangGraph Store para persistencia durable cross-thread.

---

## Troubleshooting

### El agente no encuentra resultados

1. Verificar que los MCP servers están corriendo: `docker compose ps`
2. Verificar que `BRAVE_API_KEY` está configurada en `.env`
3. Probar el MCP directamente: `python scripts/test_brave_mcp.py`

### Error de conexión con LiteLLM

1. Verificar `LITELLM_BASE_URL` y `LITELLM_API_KEY` en `.env`
2. Probar conectividad: `python scripts/test_litellm.py`
3. Asegurar que el modelo soporta **tool calling** (requerido para deepagents)

### El ChatTeamsAgent no responde

1. Verificar que el backend está corriendo: `curl http://localhost:8000/api/health`
2. Revisar logs del backend para errores de inicialización del agente
3. El agente es singleton con lazy init — el primer request tarda más

### Error en Playwright MCP

1. Verificar que el container Docker está corriendo: `docker logs aifoundry_playwright_mcp`
2. El Playwright MCP necesita Chromium — verificar que la imagen Docker lo incluye
3. Probar directamente: `python scripts/test_playwright_mcp.py`

### Errores de red / timeout

El ScraperAgent tiene retry logic integrado para errores de red recuperables:
- Reintentos automáticos con backoff
- Reset de memoria en caso de error persistente
- Logs detallados del callback handler (`AgentCallbackHandler`)

---

<p align="center">
  <a href="../README.md">← Volver al README</a> · <a href="MCP.md">MCP Servers →</a>
</p>