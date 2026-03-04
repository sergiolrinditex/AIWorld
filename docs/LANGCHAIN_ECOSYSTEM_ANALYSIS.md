# 🔗 Ecosistema LangChain — Análisis y Decisiones de Arquitectura

> Análisis del ecosistema LangChain y cómo AIWorld usa sus diferentes capas para construir agentes de IA.

**Versión**: 2.0.0
**Última actualización**: Abril 2026

---

## 📖 Índice

1. [El Ecosistema LangChain](#el-ecosistema-langchain)
2. [LangChain vs LangGraph vs deepagents](#langchain-vs-langgraph-vs-deepagents)
3. [Cómo AIWorld usa cada capa](#cómo-aiworld-usa-cada-capa)
4. [Decisiones de Arquitectura](#decisiones-de-arquitectura)
5. [Dependencias y Paquetes](#dependencias-y-paquetes)
6. [Patrones de Diseño](#patrones-de-diseño)
7. [Referencias](#referencias)

---

## El Ecosistema LangChain

LangChain ha evolucionado de un framework monolítico a un **ecosistema modular** de librerías especializadas:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ecosistema LangChain (2026)                   │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │   langchain-core  │  │   langchain       │  │  deepagents  │  │
│  │                   │  │                   │  │              │  │
│  │  Abstracciones:   │  │  Framework:       │  │  Batteries-  │  │
│  │  • Messages       │  │  • create_agent   │  │  included:   │  │
│  │  • Tools          │  │  • Chains         │  │              │  │
│  │  • Prompts        │  │  • Retrievers     │  │  • create_   │  │
│  │  • Chat Models    │  │  • Agents         │  │    deep_     │  │
│  │  • Runnables      │  │  • Output Parsers │  │    agent()   │  │
│  └────────┬──────────┘  └────────┬──────────┘  │  • Planning  │  │
│           │                      │              │  • Subagents │  │
│           └──────────┬───────────┘              │  • Filesystem│  │
│                      │                          │  • Memory    │  │
│            ┌─────────▼──────────┐               └──────┬───────┘  │
│            │    langgraph       │                       │         │
│            │                    │◄──────────────────────┘         │
│            │  Runtime:          │                                  │
│            │  • State machines  │  ┌──────────────────────────┐   │
│            │  • Checkpointers   │  │  langchain-mcp-adapters  │   │
│            │  • Streaming       │  │                          │   │
│            │  • Memory Store    │  │  MCP ↔ LangChain tools   │   │
│            └────────────────────┘  └──────────────────────────┘   │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │ langchain-openai  │  │ langchain-        │                     │
│  │                   │  │ community         │                     │
│  │ ChatOpenAI        │  │                   │                     │
│  │ (LiteLLM proxy)   │  │ Integraciones     │                     │
│  └──────────────────┘  └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## LangChain vs LangGraph vs deepagents

### ¿Cuándo usar cada uno?

Según la [documentación oficial de LangChain](https://docs.langchain.com/oss/python/langchain/overview):

| Librería | Cuándo usar | Complejidad |
|----------|------------|-------------|
| **LangChain** (`create_agent`) | Agentes simples con tools | Baja |
| **LangGraph** (custom graph) | Workflows custom, control total del flujo | Media-Alta |
| **deepagents** (`create_deep_agent`) | Agentes complejos, batteries-included | Media (abstraído) |

### LangChain (`langchain`)

> "LangChain is the easy way to start building completely custom agents and applications powered by LLMs."

- `create_agent()` → crea un agente ReAct simple con tools
- Ideal para agentes especializados de una sola tarea
- **AIWorld lo usa para**: `ScraperAgent`

### LangGraph (`langgraph`)

> "LangGraph is a framework for building agentic and multi-agent applications."

- Grafos de estado para workflows complejos
- Checkpointers para persistencia de estado
- Streaming de eventos
- **AIWorld lo usa indirectamente**: como runtime de los agentes (tanto ScraperAgent como ChatTeamsAgent)

### deepagents (`deepagents`)

> "deepagents is a standalone library built on top of LangChain's core building blocks. It uses the LangGraph runtime for durable execution, streaming, human-in-the-loop and other features."

Según la [documentación oficial](https://docs.langchain.com/oss/python/deepagents/overview):

- **Agent harness**: mismo loop de tool-calling, pero con herramientas built-in
- **Planning y task decomposition**: via `write_todos` tool
- **Context management**: file system tools (`ls`, `read_file`, `write_file`, `edit_file`)
- **Subagent spawning**: via `task` tool para delegar subtareas
- **Long-term memory**: via LangGraph's Memory Store
- **Pluggable filesystem backends**: in-memory, local disk, LangGraph store, sandboxes
- **AIWorld lo usa para**: `ChatTeamsAgent`

---

## Cómo AIWorld usa cada capa

### Capa 1: ScraperAgent → LangChain

```python
# aifoundry/app/core/aiagents/scraper/agent.py
from langchain.agents import create_agent

# Agente ReAct simple con tools MCP + locales
agent = create_agent(
    model=ChatOpenAI(...),        # langchain-openai → LiteLLM proxy
    tools=[brave_search, playwright, simple_scrape_url],
    prompt=system_prompt,
)
```

**¿Por qué LangChain aquí?**
- El ScraperAgent es un agente **especializado** en una sola tarea (scraping)
- No necesita planning, subagents ni filesystem
- ReAct pattern es suficiente: razonar → buscar → extraer → responder
- `create_agent()` es simple y directo

### Capa 2: ChatTeamsAgent → deepagents

```python
# aifoundry/app/core/agenticai/deepagents/chat_teams/agent.py
from deepagents import create_deep_agent

# Deep agent conversacional que orquesta ScraperAgents
agent = create_deep_agent(
    tools=[search_electricity, search_salary, search_social_comments, ...mcp_tools],
    system_prompt=SYSTEM_PROMPT,
)
```

**¿Por qué deepagents aquí?**
- El ChatTeamsAgent es un **orquestador** que debe decidir entre múltiples herramientas
- Necesita mantener contexto de conversación multi-turn
- Se beneficia de las capacidades built-in: planning, context management, streaming
- `create_deep_agent()` abstrae la complejidad de LangGraph

### Capa transversal: langchain-mcp-adapters

```python
# aifoundry/app/core/aiagents/scraper/tool_executor.py
from langchain_mcp_adapters.client import MultiServerMCPClient

# Conecta MCP servers → LangChain tools
async with MultiServerMCPClient(mcp_configs) as client:
    tools = client.get_tools()  # MCP tools como LangChain tools
```

**¿Por qué langchain-mcp-adapters?**
- Convierte herramientas MCP (protocolo estándar) en tools LangChain
- Permite usar MCP servers desde cualquier agente (ScraperAgent o ChatTeamsAgent)
- Descubrimiento dinámico de herramientas

### Capa de LLM: langchain-openai → LiteLLM

```python
# aifoundry/app/config.py
llm = ChatOpenAI(
    model=settings.litellm_model,
    base_url=settings.litellm_base_url,  # LiteLLM proxy
    api_key=settings.litellm_api_key,
)
```

**¿Por qué LiteLLM?**
- Gateway universal a cualquier proveedor de LLM (OpenAI, Anthropic, Azure, etc.)
- Permite cambiar de modelo sin modificar código
- Compatible con la interfaz OpenAI que usa `langchain-openai`

---

## Decisiones de Arquitectura

### 1. Dos capas de agentes en vez de una

**Decisión**: Separar en `ScraperAgent` (task-specific) + `ChatTeamsAgent` (orchestrator).

**Motivo**: 
- **Separación de responsabilidades**: cada ScraperAgent se enfoca en un dominio
- **Reutilización**: los ScraperAgents se pueden usar directamente via REST API
- **Escalabilidad**: añadir un nuevo dominio = crear config.json + tool wrapper
- **Testing**: cada capa se testea independientemente

### 2. deepagents para el orquestador (no LangGraph custom)

**Decisión**: Usar `create_deep_agent()` en vez de construir un grafo LangGraph custom.

**Motivo**:
- deepagents es el approach recomendado por LangChain para agentes complejos
- Proporciona planning, subagents, context management out-of-the-box
- Menos código que mantener vs un grafo LangGraph custom
- Facilita upgrades futuros (human-in-the-loop, long-term memory, etc.)

### 3. MCP para herramientas externas (no integraciones directas)

**Decisión**: Usar MCP servers (Brave Search, Playwright) en vez de integrar APIs directamente.

**Motivo**:
- **Estándar**: MCP es un protocolo estándar con amplio soporte
- **Desacoplamiento**: los MCP servers corren en Docker, independientes del backend
- **Reutilización**: las herramientas MCP se pueden usar desde cualquier agente
- **Ecosistema**: hay MCP servers para todo tipo de herramientas (GitHub, Slack, etc.)

### 4. LiteLLM proxy en vez de conexión directa a LLMs

**Decisión**: Todo acceso a LLMs pasa por un proxy LiteLLM.

**Motivo**:
- **Flexibilidad**: cambiar de modelo/proveedor sin tocar código
- **Configuración centralizada**: un único punto de configuración (.env)
- **Compatibilidad**: LiteLLM traduce a la interfaz OpenAI que usa langchain-openai
- **Corporativo**: permite usar modelos internos de Inditex a través del proxy

### 5. InMemorySaver para checkpoints (por ahora)

**Decisión**: Usar `InMemorySaver` de LangGraph para persistencia de estado.

**Motivo actual**:
- Simple y funcional para desarrollo y MVP
- No requiere infraestructura adicional (base de datos)

**Limitación conocida**:
- Se pierde al reiniciar el servidor
- No es apto para producción multi-instancia

**Plan futuro**: migrar a LangGraph Store o base de datos persistente.

---

## Dependencias y Paquetes

### Paquetes LangChain en pyproject.toml

```toml
[project.dependencies]
deepagents = "..."           # create_deep_agent (batteries-included)
langchain = "..."            # create_agent, chains, tools
langgraph = "..."            # Runtime (state, checkpointers, streaming)
langchain-core = "..."       # Abstracciones base
langchain-openai = "..."     # ChatOpenAI (LiteLLM compatible)
langchain-mcp-adapters = "..." # MCP ↔ LangChain bridge
```

### Relación entre paquetes

```
deepagents
├── langchain-core     (abstracciones)
├── langgraph          (runtime)
└── langchain          (agents, tools)

langchain
├── langchain-core     (abstracciones)
└── langgraph          (runtime opcional)

langchain-openai       (ChatOpenAI)
└── langchain-core

langchain-mcp-adapters (MCP bridge)
└── langchain-core
```

---

## Patrones de Diseño

### 1. Singleton Pattern (ChatTeamsAgent)

```python
class ChatTeamsAgent:
    """Singleton con lazy initialization."""
    _instance = None
    _agent = None

    async def _ensure_agent(self):
        if self._agent is None:
            self._agent = create_deep_agent(...)
```

**Por qué**: El ChatTeamsAgent mantiene estado (memoria de conversaciones). Una sola instancia evita duplicar memoria y conexiones MCP.

### 2. Config-driven Agents (ScraperAgent)

```python
# Un único agente parametrizado por config.json
agent = ScraperAgent("electricity", config=load_config("electricity"))
agent = ScraperAgent("salary", config=load_config("salary"))
```

**Por qué**: Permite crear nuevos dominios sin escribir nuevo código de agente.

### 3. Tool Wrapper Pattern

```python
@tool
async def search_electricity(query: str, country: str = "ES") -> str:
    """Wrapper que instancia ScraperAgent y ejecuta."""
    agent = ScraperAgent("electricity", ...)
    return str(await agent.run(query=query, country=country))
```

**Por qué**: Convierte ScraperAgents en tools que el ChatTeamsAgent puede invocar.

### 4. SSE Streaming Pattern

```python
async def chat(message: str, thread_id: str) -> AsyncIterator[ChatEvent]:
    async for event in agent.astream_events(..., version="v2"):
        yield process_event(event)
```

**Por qué**: Permite respuestas en tiempo real sin esperar a que el agente termine.

### 5. ToolResolver Pattern

```python
class ToolResolver:
    """Combina tools locales + MCP tools dinámicamente."""
    async def get_tools(self):
        return local_tools + await self._load_mcp_tools()
```

**Por qué**: Desacopla la carga de herramientas del agente. Permite añadir MCP servers sin modificar el agente.

---

## Referencias

### Documentación oficial

- [LangChain Overview](https://docs.langchain.com/oss/python/langchain/overview)
- [Deep Agents Overview](https://docs.langchain.com/oss/python/deepagents/overview)
- [Deep Agents Quickstart](https://docs.langchain.com/oss/python/deepagents/get-started/quickstart)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)

### Documentación del proyecto

- [README.md](../README.md) — Documentación principal de AIWorld
- [docs/AGENTS.md](AGENTS.md) — Guía completa de agentes
- [docs/MCP.md](MCP.md) — Documentación de MCP servers
- [docs/HEFESTO_DESIGN.md](HEFESTO_DESIGN.md) — Diseño del frontend Hefesto

---

<p align="center">
  <a href="../README.md">← Volver al README</a> · <a href="HEFESTO_DESIGN.md">← Hefesto</a>
</p>