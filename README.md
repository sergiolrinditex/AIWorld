# AIWorld

**Plataforma de agentes de AI para investigación web y extracción de datos estructurados.**

---

## ¿Qué es AIFoundry?

AIFoundry es el backend de AIWorld: una plataforma diseñada para soportar los **4 paradigmas de AI** — desde workflows simples hasta sistemas multi-agente autónomos.

![AIFoundry — Los 4 paradigmas de AI](aifoundry/app/core/core_aifoundry.gif)

### Los 4 paradigmas de AI

| Paradigma | Funcionalidad | Mejor uso | Fortaleza | Ejemplo |
|-----------|---------------|-----------|-----------|---------|
| **LLM Workflow** | Predicción de tokens basada en input | Generación de texto y resúmenes | Rápido, baja complejidad, fácil de desplegar | Chatbots, bots de email |
| **RAG** | Recuperación inteligente de fuentes de conocimiento | Q&A preciso desde fuentes variadas | Mayor precisión con datos externos | Graph RAG, Advanced RAG, Modular RAG |
| **AI Agent** ✅ | Acción autónoma usando componentes | Workflows que requieren tools y razonamiento | Automatización con planificación + razonamiento | ReAct Agent, Rewoo Agent |
| **Agentic AI** | Sistema multi-agente autónomo | Tareas a gran escala que requieren colaboración | Flexible, reparte trabajo entre agentes especializados | [Deep Agents](https://www.langchain.com/deep-agents), CUA, Embodied Agents |

> **Estado actual**: AIFoundry implementa el paradigma **AI Agent** con `ScraperAgent` (ReAct). Los paradigmas LLM Workflow, RAG y Agentic AI están en el roadmap.

### ¿Cómo funciona hoy?

Actualmente AIFoundry usa un único agente genérico (`ScraperAgent`) que sigue el patrón **AI Agent** del diagrama: el usuario envía un prompt, el agente usa *Memory*, *Reasoning*, *Planning* y *Tools* (Brave Search, Playwright, scraping local) para investigar la web y devolver datos estructurados via Pydantic.

## Arquitectura

```
┌──────────────────────────────────────────────────────┐
│                    AIFoundry                          │
│              FastAPI Backend (Python)                 │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │             ScraperAgent (ReAct)              │    │
│  │  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │    │
│  │  │ Memory   │ │ Tool     │ │ Output      │  │    │
│  │  │ Manager  │ │ Resolver │ │ Parser      │  │    │
│  │  └──────────┘ └──────────┘ └─────────────┘  │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  ┌───────────────┐  ┌───────────────────────────┐    │
│  │ LLM (LiteLLM) │  │ MCP Servers               │    │
│  │ Claude/GPT/... │  │ ┌─────────┐ ┌──────────┐ │    │
│  └───────────────┘  │ │ Brave   │ │Playwright│ │    │
│                      │ │ Search  │ │ Browser  │ │    │
│                      │ └─────────┘ └──────────┘ │    │
│                      └───────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

---

## Dominios disponibles

| Dominio | Config | Structured Output | Descripción |
|---------|--------|-------------------|-------------|
| **Salarios** | `salary/config.json` | `SalaryResponse` | Investiga salarios por empresa, puesto y país |
| **Electricidad** | `electricity/config.json` | `ElectricityResponse` | Precios de electricidad por país y proveedor |
| **Comentarios Sociales** | `social_comments/config.json` | `SocialCommentsResponse` | Monitoriza opiniones en redes sociales |

## Stack tecnológico

| Tecnología | Propósito |
|------------|-----------|
| **LangGraph** | Runtime de agentes ReAct con checkpointer |
| **LangChain** | Orquestación de LLMs y tools |
| **LiteLLM** | Proxy multi-proveedor (Bedrock, OpenAI, Anthropic) |
| **FastAPI** | API REST con docs OpenAPI automáticas |
| **MCP** | Model Context Protocol para tools externas |
| **Pydantic** | Validación de datos y structured output |

## Ecosistema LangChain y los 4 paradigmas

El ecosistema [LangChain](https://www.langchain.com) proporciona las herramientas para implementar los 4 paradigmas. Sus 3 productos son **capas complementarias**, no alternativas:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Deep Agents                              │
│            (Agentic AI — tareas largas, sub-agentes)             │
├─────────────────────────────────────────────────────────────────┤
│                          LangGraph                               │
│    (AI Agent + Agentic AI — runtime, grafos, single/multi)       │
├─────────────────────────────────────────────────────────────────┤
│                          LangChain                               │
│       (LLM Workflow + RAG + AI Agent — chains, retrievers, tools)│
├─────────────────────────────────────────────────────────────────┤
│                        LLM Provider                              │
│           (Bedrock, OpenAI, Anthropic via LiteLLM)               │
└─────────────────────────────────────────────────────────────────┘
```

| Producto | Nivel | Paradigma(s) |
|----------|-------|-------------|
| [**LangChain**](https://www.langchain.com/langchain) | Alto nivel — `create_agent`, LCEL chains, retrievers, 1000+ integraciones | **LLM Workflow** + **RAG** + **AI Agent** |
| [**LangGraph**](https://www.langchain.com/langgraph) | Bajo nivel — grafos de estado, checkpoints, human-in-the-loop | **AI Agent** + **Agentic AI** |
| [**Deep Agents**](https://www.langchain.com/deep-agents) | Máxima autonomía — planning, sub-agentes, memoria filesystem | **Agentic AI** |

> `create_agent` de LangChain usa LangGraph como runtime por debajo. LangGraph da más control cuando necesitas grafos custom o multi-agent. Deep Agents es la implementación de referencia de Agentic AI.
>
> 📖 Ver análisis completo: [docs/LANGCHAIN_ECOSYSTEM_ANALYSIS.md](docs/LANGCHAIN_ECOSYSTEM_ANALYSIS.md)

## Estructura del proyecto

```
aifoundry/
├── app/
│   ├── api/                         # Endpoints FastAPI
│   │   ├── router.py                # Routes: /health, /agents, /agents/{name}/run
│   │   └── schemas.py               # Request/Response schemas
│   ├── config.py                    # Settings (Pydantic BaseSettings)
│   ├── main.py                      # FastAPI app + lifespan
│   ├── core/
│   │   ├── aiagents/                # AI Agents
│   │   │   └── scraper/             # Agente genérico de scraping
│   │           ├── agent.py         # ScraperAgent (orquestador)
│   │           ├── memory.py        # InMemoryManager / NullMemoryManager
│   │           ├── tool_executor.py # ToolResolver (MCP + local tools)
│   │           ├── output_parser.py # OutputParser (structured + text)
│   │           ├── prompts.py       # System prompt builder
│   │           ├── tools.py         # Local tools (scraper, country info)
│   │           ├── config_schema.py # AgentConfig Pydantic model
│   │           ├── salary/          # config.json para salarios
│   │           ├── electricity/     # config.json para electricidad
│   │           └── social_comments/ # config.json para redes sociales
│   │   └── models/
│   │       └── llm.py              # LLM singleton (init_chat_model + LiteLLM)
│   ├── mcp_servers/                 # Servidores MCP (Brave Search, Playwright)
│   ├── schemas/                     # Response models (SalaryResponse, etc.)
│   └── utils/                       # Utilidades (parsing, scraping, country info)
├── tests/                           # 211 tests (unit + integration)
└── docker/                          # Dockerfiles
```

## API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/agents` | Lista de agentes disponibles |
| `GET` | `/api/agents/{name}/config` | Configuración de un agente |
| `POST` | `/api/agents/{name}/run` | Ejecuta un agente (síncrono) |

---

## Quick Start

```bash
# 1. Clonar el repositorio
git clone https://github.com/sergiolrinditex/AIWorld.git
cd AIWorld

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias
pip install -e ".[dev]"

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 5. Levantar servicios MCP (Docker)
docker compose up -d

# 6. Ejecutar el servidor
uvicorn aifoundry.app.main:app --reload --port 8000
```

### Configuración (.env)

```bash
# LLM
LITELLM_API_BASE=https://your-litellm-proxy.com
LITELLM_API_KEY=sk-your-key
LITELLM_MODEL=bedrock/claude-sonnet-4

# MCP Servers
BRAVE_SEARCH_MCP_URL=http://localhost:8082/mcp
PLAYWRIGHT_MCP_URL=http://localhost:8931/mcp

# Brave Search
BRAVE_API_KEY=your-brave-key
```

## Tests

```bash
# Ejecutar todos los tests unitarios (211)
python -m pytest aifoundry/tests/unit/ -v

# Tests de integración
python -m pytest aifoundry/tests/integration/ -v

# Scripts de test end-to-end (requiere servicios MCP + LLM)
python scripts/test_salary_agent.py
python scripts/test_electricity_agent.py
python scripts/test_social_comments_agent.py
```

## Crear un nuevo dominio

Para añadir un nuevo tipo de agente (ej: precios de gasolina):

1. **Crear config.json** en `aifoundry/app/core/aiagents/scraper/fuel/config.json`
2. **Crear response model** en `aifoundry/app/schemas/agent_responses.py`
3. El discovery automático del router lo detecta (busca `**/config.json` recursivamente)

No se necesita crear clases Python — `ScraperAgent` es genérico y se adapta vía config.

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [docs/AGENTS.md](docs/AGENTS.md) | Guía completa de agentes: configuración, tools, structured output |
| [docs/MCP.md](docs/MCP.md) | Arquitectura MCP: Brave Search y Playwright |
| [docs/FRONTEND_DESIGN_PROPOSAL.md](docs/FRONTEND_DESIGN_PROPOSAL.md) | Propuesta de diseño del frontend (no implementado) |
| [docs/LANGCHAIN_ECOSYSTEM_ANALYSIS.md](docs/LANGCHAIN_ECOSYSTEM_ANALYSIS.md) | Análisis: LangChain + LangGraph + Deep Agents vs. los 4 paradigmas |

---

## Roadmap

### ✅ Completado

- Agente ReAct genérico (`ScraperAgent`) con config JSON por dominio
- Structured output nativo via `response_format` (1 sola llamada LLM)
- Integración MCP (Brave Search + Playwright)
- Memoria conversacional con `InMemorySaver`
- API REST con FastAPI
- 211 tests unitarios y de integración
- Refactoring modular: `memory.py`, `tool_executor.py`, `output_parser.py`

### 🔧 Próximos pasos — Infraestructura

- [ ] Autenticación API Key (`X-API-Key` header)
- [ ] Streaming SSE (`POST /agents/{name}/stream`)
- [ ] Memoria persistente (Redis + SQLite fallback)
- [ ] Frontend React (AIWorld Client) — ver [propuesta](docs/FRONTEND_DESIGN_PROPOSAL.md)
- [ ] Integración Microsoft Teams

### 📋 Próximos paradigmas (ver [diagrama](#los-4-paradigmas-de-ai))

- [ ] **LLM Workflow** — Pipelines simples de generación y resumen (chatbots, email drafting)
- [ ] **RAG** — Retrieval Augmented Generation con vector DB para Q&A sobre documentos internos
- [ ] **Agentic AI** — Multi-agent workflows con agentes especializados que colaboran entre sí

---

## Licencia

MIT