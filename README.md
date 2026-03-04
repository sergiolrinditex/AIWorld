<p align="center">
  <img src="aifoundry/app/core/core_aifoundry.gif" alt="AIWorld" width="120" />
</p>

<h1 align="center">🌍 AIWorld</h1>

<p align="center">
  <strong>Ecosistema de agentes de IA para investigación web y extracción de datos estructurados</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-≥3.11-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19.x-61DAFB?logo=react&logoColor=black" alt="React" /></a>
  <a href="https://docs.langchain.com/oss/python/deepagents/overview"><img src="https://img.shields.io/badge/deepagents-SDK-1C3C3C?logo=langchain&logoColor=white" alt="DeepAgents" /></a>
  <a href="https://docs.langchain.com/oss/python/langchain/overview"><img src="https://img.shields.io/badge/LangChain-v1-1C3C3C?logo=langchain&logoColor=white" alt="LangChain" /></a>
  <a href="https://modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP-Protocol-blueviolet" alt="MCP" /></a>
</p>

<p align="center">
  AIWorld es una plataforma de <a href="https://www.inditex.com">Inditex / PeopleTech</a> que combina agentes de IA especializados con una interfaz conversacional para Microsoft Teams.<br/>
  Construido sobre el ecosistema <strong>LangChain</strong>: utiliza <strong>deepagents</strong> como harness de alto nivel y <strong>LangChain + LangGraph</strong> como framework y runtime subyacentes.
</p>

---

## 📖 Índice

- [Visión General](#visión-general)
- [Taxonomía de Agentes — AI Agent vs Agentic AI](#taxonomía-de-agentes--ai-agent-vs-agentic-ai)
- [Posicionamiento en el Ecosistema LangChain](#posicionamiento-en-el-ecosistema-langchain)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Flujo de Datos Completo](#flujo-de-datos-completo)
- [Stack Tecnológico](#stack-tecnológico)
- [Componentes Principales](#componentes-principales)
  - [ChatTeamsAgent (Deep Agent)](#-chatteamsagent-deep-agent)
  - [ScraperAgent (ReAct)](#-scraperagent-react)
  - [MCP Servers (Model Context Protocol)](#-mcp-servers-model-context-protocol)
  - [Hefesto (Frontend)](#-hefesto-frontend)
  - [LiteLLM Proxy](#-litellm-proxy)
- [Arquitectura Config-Driven](#arquitectura-config-driven)
- [Streaming SSE — Protocolo de Eventos](#streaming-sse--protocolo-de-eventos)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Dominios de Scraping](#dominios-de-scraping)
- [Tests](#tests)
- [Seguridad y Resiliencia](#seguridad-y-resiliencia)
- [Observabilidad y Monitoreo](#observabilidad-y-monitoreo)
- [Documentación Adicional](#documentación-adicional)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Licencia](#licencia)

---

## Visión General

AIWorld implementa un **sistema multi-agente de dos capas** para investigación web y extracción de datos estructurados. La plataforma permite a los usuarios de Microsoft Teams hacer preguntas en lenguaje natural (como *"¿Cuánto cuesta la luz en España?"* o *"¿Cuál es el salario medio de un ingeniero en Alemania?"*) y obtener respuestas estructuradas y verificadas extraídas de la web en tiempo real.

El sistema se organiza en tres grandes bloques:

| Bloque | Nombre | Responsabilidad |
|--------|--------|-----------------|
| **Frontend** | [Hefesto](#-hefesto-frontend) | Interfaz conversacional React embebida como Tab App en Microsoft Teams |
| **Backend** | [AIFoundry](#arquitectura-del-sistema) | API FastAPI con agentes de IA orquestados, MCP tools y streaming SSE |
| **Infraestructura** | [MCP Servers + LiteLLM](#-mcp-servers-model-context-protocol) | Servidores Docker para búsqueda web, scraping y gateway a modelos LLM |

La interacción sigue este flujo: **Usuario (Teams) → Hefesto → ChatTeamsAgent (Deep Agent) → ScraperAgents (ReAct) → MCP Tools (Brave Search + Playwright) → Respuesta estructurada en streaming**.

---

## Taxonomía de Agentes — AI Agent vs Agentic AI

AIWorld implementa una taxonomía deliberada de dos niveles que refleja diferentes grados de autonomía y complejidad:

### Capa 1 — AI Agent (`ScraperAgent`)

Un **AI Agent** es un agente con un propósito específico y acotado. En AIWorld, el `ScraperAgent` es un agente ReAct (Reasoning + Acting) creado con [`langchain.agents.create_agent()`](https://docs.langchain.com/oss/python/langchain/overview) — la nueva API estándar de LangChain v1 que reemplaza al antiguo `create_react_agent` de LangGraph.

Características del AI Agent:
- **Propósito único**: cada instancia es un scraper especializado en un dominio (electricidad, salarios, comentarios sociales)
- **Config-driven**: configurado por un archivo `config.json` que define queries, prompts de extracción y países soportados
- **Herramientas acotadas**: usa MCP tools (Brave Search, Playwright) y `simple_scrape_url`
- **Structured output**: devuelve datos tipados via Pydantic `response_model`
- **Efímero**: se crea, ejecuta y destruye por cada invocación

### Capa 2 — Agentic AI (`ChatTeamsAgent`)

Una **Agentic AI** es un sistema de agentes orquestado de mayor complejidad. En AIWorld, el `ChatTeamsAgent` es un Deep Agent creado con [`deepagents.create_deep_agent()`](https://docs.langchain.com/oss/python/deepagents/overview) — la librería "batteries-included" de LangChain para agentes complejos.

Según la [documentación oficial de deepagents](https://docs.langchain.com/oss/python/deepagents/overview):

> *"Deep agents are the easiest way to start building agents and applications powered by LLMs—with builtin capabilities for task planning, file systems for context management, subagent-spawning, and long-term memory."*

Características de la Agentic AI:
- **Conversacional**: mantiene contexto multi-turn con checkpointing por `thread_id`
- **Orquestador**: decide qué ScraperAgents invocar según la petición del usuario
- **Planificación**: descompone tareas complejas en pasos (capacidad nativa de deepagents)
- **Streaming en tiempo real**: respuestas parciales, thinking blocks y tool calls via SSE
- **Persistente**: singleton con lazy initialization y memoria por sesión

```
┌──────────────────────────────────────────────────────────────┐
│                    Agentic AI (Capa 2)                        │
│              ChatTeamsAgent — Deep Agent                       │
│                                                               │
│    deepagents.create_deep_agent()                            │
│    • Planning    • Subagent-spawning                         │
│    • Memory      • Context compression                       │
│                                                               │
│    ┌─────────┐  ┌─────────┐  ┌──────────────┐               │
│    │ search_ │  │ search_ │  │ search_      │  Tools         │
│    │ electr. │  │ salary  │  │ social_comm. │  (wrappers)    │
│    └────┬────┘  └────┬────┘  └──────┬───────┘               │
│         │            │              │                         │
│    ┌────▼────────────▼──────────────▼────────────────────┐   │
│    │              AI Agent (Capa 1)                       │   │
│    │         ScraperAgent — ReAct Agent                   │   │
│    │                                                      │   │
│    │    langchain.agents.create_agent()                   │   │
│    │    • Config-driven    • Structured output            │   │
│    │    • MCP tools        • Retry logic                  │   │
│    └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Posicionamiento en el Ecosistema LangChain

Según la [documentación oficial](https://docs.langchain.com/oss/python/langchain/overview), el ecosistema LangChain se organiza en tres niveles:

| Nivel | Paquete | Rol | AIWorld lo usa para |
|-------|---------|-----|---------------------|
| **Framework** | [LangChain](https://docs.langchain.com/oss/python/langchain/overview) | Abstracciones para modelos, herramientas, agentes | `ScraperAgent` (create_agent, ChatOpenAI, tools) |
| **Runtime** | [LangGraph](https://docs.langchain.com/oss/python/concepts/products) | Ejecución durable, grafos con estado, streaming, human-in-the-loop | Motor subyacente de ambos agentes (checkpointing, astream_events) |
| **Harness** | [deepagents](https://docs.langchain.com/oss/python/deepagents/overview) | Agente "batteries-included" con planning, subagents, filesystem, memory | `ChatTeamsAgent` (create_deep_agent) |

La [documentación de deepagents](https://docs.langchain.com/oss/python/deepagents/customization) explica la relación:

> *"deepagents is a standalone library built on top of LangChain's core building blocks for agents. It uses the LangGraph runtime for durable execution, streaming, human-in-the-loop, and other features."*

AIWorld aprovecha **los tres niveles** del ecosistema:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Ecosistema LangChain                            │
│                                                                      │
│  ┌───────────────┐    ┌───────────────┐    ┌─────────────────────┐  │
│  │   LangChain    │    │   LangGraph    │    │     deepagents      │  │
│  │   (Framework)  │    │   (Runtime)    │    │     (Harness)       │  │
│  │                │    │                │    │                     │  │
│  │  • ChatOpenAI  │    │  • StateGraph  │    │  • create_deep_     │  │
│  │  • create_     │    │  • Checkpoints │    │    agent()          │  │
│  │    agent()     │    │  • astream_    │    │  • Task planning    │  │
│  │  • BaseTool    │    │    events      │    │  • Subagent-        │  │
│  │  • Prompts     │    │  • Store       │    │    spawning         │  │
│  │  • Messages    │    │  • HITL        │    │  • File system      │  │
│  │                │    │                │    │  • Long-term memory │  │
│  └───────┬────────┘    └───────┬────────┘    └──────────┬──────────┘  │
│          │                     │                        │             │
│          └──────────┬──────────┘                        │             │
│                     │                                   │             │
│          ┌──────────▼──────────┐            ┌───────────▼──────────┐  │
│          │   ScraperAgent      │            │   ChatTeamsAgent     │  │
│          │   (AIWorld)         │            │   (AIWorld)          │  │
│          └─────────────────────┘            └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

Adicionalmente, AIWorld integra [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) usando [`langchain-mcp-adapters`](https://docs.langchain.com/oss/python/langchain/mcp) — la librería oficial de LangChain para conectar herramientas MCP:

> *"Model Context Protocol (MCP) is an open protocol that standardizes how applications provide tools and context to LLMs. LangChain agents can use tools defined on MCP servers using the langchain-mcp-adapters library."*

---

## Arquitectura del Sistema

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USUARIO                                      │
│                     (Microsoft Teams)                                 │
└──────────────┬───────────────────────────────────────────────────────┘
               │ HTTPS
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      HEFESTO (Frontend)                               │
│                React 19 + TypeScript 5.9 + Vite 7                    │
│                        Puerto: 5173                                   │
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐   │
│  │  ChatInput   │  │ MessageList  │  │  ThinkingBlock            │   │
│  │  Component   │  │ + MessageBub │  │  + ToolBlock              │   │
│  └─────────────┘  └──────────────┘  └───────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  useChat() hook                                               │    │
│  │    ├── chatService.ts ──► SSE EventSource (fetch + ReadableStream)│
│  │    ├── Estado: messages[], isLoading, threadId                 │    │
│  │    └── Parseo en tiempo real de eventos SSE                   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  @microsoft/teams-js SDK                                      │    │
│  │    └── teams-manifest/manifest.json (Tab App registration)    │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────┬───────────────────────────────────────────────────────┘
               │ SSE (Server-Sent Events) over HTTP POST
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     AIFOUNDRY (Backend)                                │
│                FastAPI + Uvicorn (ASGI)                                │
│                      Puerto: 8000                                     │
│                                                                       │
│  ┌─── API Layer ─────────────────────────────────────────────────┐   │
│  │                                                                │   │
│  │  chat_teams_router.py                router.py                │   │
│  │  ┌─────────────────────┐            ┌──────────────────────┐  │   │
│  │  │ POST /api/chat      │ (SSE)      │ GET  /api/health     │  │   │
│  │  │ POST /api/chat/sync │            │ GET  /api/agents     │  │   │
│  │  │ GET  /api/chat/     │            │ GET  /api/agents/    │  │   │
│  │  │      history/{id}   │            │      {name}/config   │  │   │
│  │  └─────────┬───────────┘            │ POST /api/agents/    │  │   │
│  │            │                        │      {name}/run      │  │   │
│  │            │                        └──────────┬───────────┘  │   │
│  └────────────┼───────────────────────────────────┼──────────────┘   │
│               │                                   │                   │
│  ┌────────────▼───────────────────────────────────▼──────────────┐   │
│  │                    AGENT LAYER                                 │   │
│  │                                                                │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │         ChatTeamsAgent (Deep Agent — Singleton)          │  │   │
│  │  │                                                          │  │   │
│  │  │  deepagents.create_deep_agent(                          │  │   │
│  │  │      model=ChatOpenAI(→ LiteLLM Proxy),                │  │   │
│  │  │      tools=[...],                                       │  │   │
│  │  │      system_prompt=SYSTEM_PROMPT,                       │  │   │
│  │  │  )                                                      │  │   │
│  │  │                                                          │  │   │
│  │  │  Memory: InMemorySaver (checkpoints por thread_id)      │  │   │
│  │  │  Streaming: astream_events(version="v2")                │  │   │
│  │  │                                                          │  │   │
│  │  │  Tools registradas:                                     │  │   │
│  │  │  ┌──────────────┐ ┌────────────┐ ┌──────────────────┐  │  │   │
│  │  │  │ search_      │ │ search_    │ │ search_social_   │  │  │   │
│  │  │  │ electricity  │ │ salary     │ │ comments         │  │  │   │
│  │  │  └──────┬───────┘ └─────┬──────┘ └────────┬─────────┘  │  │   │
│  │  │         │               │                  │            │  │   │
│  │  │  ┌──────┴───┐  ┌───────┴──┐  ┌────────────┴────────┐  │  │   │
│  │  │  │ list_    │  │ simple_  │  │ (MCP tools directos) │  │  │   │
│  │  │  │ available│  │ scrape_  │  │ brave_web_search     │  │  │   │
│  │  │  │ _agents  │  │ url      │  │ browser_navigate ... │  │  │   │
│  │  │  └──────────┘  └──────────┘  └─────────────────────┘  │  │   │
│  │  └──────────────────────┬───────────────────────────────┘  │   │
│  │                         │                                  │   │
│  │  ┌──────────────────────▼───────────────────────────────┐  │   │
│  │  │           ScraperAgent (ReAct Agent)                  │  │   │
│  │  │                                                       │  │   │
│  │  │  langchain.agents.create_agent(                      │  │   │
│  │  │      model=ChatOpenAI(→ LiteLLM Proxy),             │  │   │
│  │  │      tools=[brave_web_search, browser_*, scrape_url],│  │   │
│  │  │  )                                                    │  │   │
│  │  │                                                       │  │   │
│  │  │  Config-driven: {domain}/config.json                 │  │   │
│  │  │  Structured output: Pydantic response_model          │  │   │
│  │  │  Retry: hasta 3 intentos en errores de red           │  │   │
│  │  │  Context manager: async with ScraperAgent(...) as a  │  │   │
│  │  └───────────┬──────────────┬──────────────┬────────────┘  │   │
│  │              │              │              │                │   │
│  └──────────────┼──────────────┼──────────────┼────────────────┘   │
│                 │              │              │                     │
│  ┌──────────────▼──────────────▼──────────────▼────────────────┐   │
│  │              TOOL LAYER (ToolResolver)                        │   │
│  │                                                               │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │   │
│  │  │ MultiServerMCP  │  │ MultiServerMCP  │  │ simple_      │ │   │
│  │  │ Client          │  │ Client          │  │ scrape_url   │ │   │
│  │  │ (Brave Search)  │  │ (Playwright)    │  │ (httpx)      │ │   │
│  │  └────────┬────────┘  └────────┬────────┘  └──────────────┘ │   │
│  └───────────┼────────────────────┼────────────────────────────┘   │
│              │                    │                                 │
└──────────────┼────────────────────┼────────────────────────────────┘
               │ streamable_http    │ streamable_http
               ▼                    ▼
┌───────────────────┐  ┌─────────────────────┐  ┌───────────────────┐
│  Brave Search     │  │   Playwright        │  │   LiteLLM Proxy   │
│  MCP Server       │  │   MCP Server        │  │                   │
│  (Docker)         │  │   (Docker)          │  │   Gateway a       │
│                   │  │                     │  │   modelos LLM     │
│  Puerto: 8082     │  │   Puerto: 8931      │  │   (OpenAI, Azure, │
│                   │  │   Chromium headless  │  │    Anthropic...)  │
│  Tool:            │  │                     │  │                   │
│  brave_web_search │  │   Tools:            │  │   Configurable    │
│                   │  │   browser_navigate  │  │   via .env        │
│  Transporte:      │  │   browser_snapshot  │  │                   │
│  streamable_http  │  │   browser_click     │  │   LITELLM_MODEL   │
│                   │  │   browser_type      │  │   LITELLM_BASE_URL│
│                   │  │   ...               │  │   LITELLM_API_KEY │
└───────────────────┘  └─────────────────────┘  └───────────────────┘
```

---

## Flujo de Datos Completo

Este es el flujo detallado de una petición del usuario desde Teams hasta la respuesta final:

```
1. USUARIO escribe en Teams: "¿Cuánto cuesta la luz en España?"
   │
2. HEFESTO (React)
   │  └─ useChat() hook captura el mensaje
   │  └─ chatService.sendMessage() abre SSE connection via fetch()
   │  └─ POST /api/chat { message: "...", thread_id: "abc123" }
   │
3. AIFOUNDRY (FastAPI)
   │  └─ chat_teams_router.py recibe la petición
   │  └─ StreamingResponse con media_type="text/event-stream"
   │
4. ChatTeamsAgent (Deep Agent)
   │  └─ Recibe HumanMessage + config { thread_id, recursion_limit }
   │  └─ astream_events(version="v2") inicia el stream
   │  └─ LLM (ChatOpenAI → LiteLLM) analiza la petición
   │  └─ Decide invocar tool: search_electricity(query="precio luz España")
   │
   │  ── SSE Event: { event: "thinking", data: "Voy a buscar..." } ──►
   │  ── SSE Event: { event: "tool_start", data: { tool: "search_electricity" } } ──►
   │
5. ScraperAgent (ReAct) — electricity domain
   │  └─ Lee config.json: query_template, extraction_prompt, countries.ES
   │  └─ Construye system prompt + human message
   │  └─ Ejecuta agente ReAct:
   │       │
   │       ├─ Paso 1: brave_web_search("precio electricidad España 2026")
   │       │  └─ → Brave Search MCP Server (Docker :8082)
   │       │  └─ ← Resultados de búsqueda con URLs
   │       │
   │       ├─ Paso 2: browser_navigate(url="https://...")
   │       │  └─ → Playwright MCP Server (Docker :8931)
   │       │  └─ ← Contenido HTML de la página
   │       │
   │       ├─ Paso 3: LLM extrae datos estructurados del contenido
   │       │  └─ Aplica extraction_prompt del config.json
   │       │
   │       └─ Retorna: structured output (Pydantic model)
   │
   │  ── SSE Event: { event: "tool_end", data: { tool: "search_electricity", output: "..." } } ──►
   │
6. ChatTeamsAgent recibe resultado del ScraperAgent
   │  └─ LLM formula respuesta final en lenguaje natural
   │  └─ Streaming token por token
   │
   │  ── SSE Event: { event: "token", data: { content: "Según los datos..." } } ──►
   │  ── SSE Event: { event: "token", data: { content: " más recientes..." } } ──►
   │  ── SSE Event: { event: "end", data: { thread_id: "abc123" } } ──►
   │
7. HEFESTO (React)
   │  └─ useChat() procesa cada evento SSE
   │  └─ Renderiza ThinkingBlock, ToolBlock, y MessageBubble progresivamente
   │  └─ Usuario ve la respuesta construirse en tiempo real
   │
8. USUARIO lee la respuesta en Teams
```

---

## Stack Tecnológico

### Backend — AIFoundry

| Tecnología | Versión | Rol en AIWorld |
|-----------|---------|----------------|
| **Python** | ≥ 3.11 | Runtime principal |
| **FastAPI** | 0.115+ | Framework web ASGI con soporte SSE nativo |
| **Uvicorn** | latest | Servidor ASGI de alto rendimiento |
| **[deepagents](https://docs.langchain.com/oss/python/deepagents/overview)** | pre-1.0 | Harness de agentes con planning, subagent-spawning, context compression, long-term memory |
| **[LangChain](https://docs.langchain.com/oss/python/langchain/overview)** | v1 | Framework de agentes: `create_agent()`, `ChatOpenAI`, `BaseTool`, messages |
| **[LangGraph](https://docs.langchain.com/oss/python/concepts/products)** | 0.4+ | Runtime subyacente: `InMemorySaver`, `astream_events`, checkpointing |
| **[langchain-mcp-adapters](https://docs.langchain.com/oss/python/langchain/mcp)** | latest | Puente MCP ↔ LangChain via `MultiServerMCPClient` |
| **langchain-openai** | latest | Integración ChatOpenAI para tool calling |
| **LiteLLM** | latest | Proxy universal a modelos LLM (OpenAI, Azure, Anthropic, etc.) |
| **Pydantic** | 2.x | Validación, settings, schemas y structured output |
| **SSE-Starlette** | latest | Server-Sent Events para FastAPI |
| **httpx** | latest | HTTP client async para `simple_scrape_url` |

### Frontend — Hefesto

| Tecnología | Versión | Rol en AIWorld |
|-----------|---------|----------------|
| **React** | 19.x | Framework UI con hooks pattern |
| **TypeScript** | 5.9 | Tipado estático end-to-end |
| **Vite** | 7.x | Build tool y dev server con HMR |
| **@microsoft/teams-js** | 2.49+ | SDK de Microsoft Teams para Tab App |
| **react-markdown** | 10.x | Renderizado de Markdown en mensajes |
| **remark-gfm** | latest | Soporte GitHub Flavored Markdown (tablas, etc.) |
| **lucide-react** | latest | Iconos SVG para la interfaz |

### Infraestructura

| Componente | Tecnología | Puerto | Transporte |
|-----------|-----------|--------|------------|
| Backend API | FastAPI + Uvicorn | 8000 | HTTP / SSE |
| Frontend dev | Vite dev server | 5173 | HTTP |
| Brave Search MCP | Docker (Node.js) | 8082 → 8080 | `streamable_http` |
| Playwright MCP | Docker (Node.js + Chromium) | 8931 | `streamable_http` |
| LiteLLM Proxy | Externo (configurable) | Configurable | HTTP (OpenAI-compatible) |

---

## Componentes Principales

### 🤖 ChatTeamsAgent (Deep Agent)

**Ubicación**: `aifoundry/app/core/agenticai/deepagents/chat_teams/`

El ChatTeamsAgent es el agente de alto nivel de AIWorld. Usa [`create_deep_agent()`](https://docs.langchain.com/oss/python/deepagents/customization) de la librería `deepagents`:

```python
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

# LLM apuntando a LiteLLM Proxy (compatible OpenAI API)
llm = ChatOpenAI(
    model=settings.litellm_model,
    base_url=settings.litellm_base_url,
    api_key=settings.litellm_api_key,
    temperature=0.3,
    streaming=True,
)

# Deep Agent con tools, system prompt y modelo
agent = create_deep_agent(
    model=llm,
    tools=[
        search_electricity,       # Wrapper → ScraperAgent(electricity)
        search_salary,            # Wrapper → ScraperAgent(salary)
        search_social_comments,   # Wrapper → ScraperAgent(social_comments)
        list_available_agents,    # Listado de agentes disponibles
        simple_scrape_url,        # Scraping directo de URL
        # + MCP tools directos (Brave Search, Playwright)
    ],
    system_prompt=SYSTEM_PROMPT,
)
```

Según la documentación de [`create_deep_agent`](https://docs.langchain.com/oss/python/deepagents/customization), las opciones de configuración incluyen: **Model**, **Tools**, **System Prompt**, **Middleware**, **Subagents**, **Backends** (virtual filesystems), **Human-in-the-loop**, **Skills** y **Memory**.

**Patrón singleton**: AIWorld implementa `ChatTeamsAgent` como singleton con lazy initialization. La primera invocación crea el agente; las siguientes reutilizan la misma instancia:

```python
class ChatTeamsAgent:
    _instance: ClassVar[Optional["ChatTeamsAgent"]] = None
    _agent = None  # Lazily initialized

    @classmethod
    def get_instance(cls) -> "ChatTeamsAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

**Memory**: Usa `InMemorySaver` de LangGraph como checkpointer, identificando cada conversación por `thread_id`. Esto permite mantener contexto multi-turn dentro de una misma sesión de chat.

**Streaming**: Usa `astream_events(version="v2")` de LangGraph para emitir eventos en tiempo real. El módulo `streaming.py` transforma estos eventos internos en el protocolo SSE de Hefesto (`ChatEvent`).

#### Archivos del módulo

| Archivo | Responsabilidad |
|---------|----------------|
| `agent.py` | Clase `ChatTeamsAgent` — singleton, streaming, invocación |
| `tools.py` | Tool wrappers (`@tool` decorados) que envuelven ScraperAgent |
| `prompts.py` | System prompt del orquestador conversacional |
| `config.py` | `ChatTeamsConfig` — configuración del agente (model, temperature, MCP URLs) |
| `memory.py` | Factory de `InMemorySaver` checkpointer |
| `streaming.py` | Formateo de eventos SSE (`ChatEvent` dataclass) |

---

### 🔍 ScraperAgent (ReAct)

**Ubicación**: `aifoundry/app/core/aiagents/scraper/`

El ScraperAgent es el agente de nivel base. Usa [`create_agent()`](https://docs.langchain.com/oss/python/langchain/overview) de LangChain v1 — la nueva API estándar que reemplaza a `create_react_agent` de LangGraph:

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=resolved_tools,  # MCP tools + simple_scrape_url
)
```

**Ciclo de vida**: El ScraperAgent usa el patrón async context manager para gestionar la conexión con MCP servers:

```python
async with ScraperAgent(agent_name="electricity", query="precio luz España") as agent:
    result = await agent.run()
    # result es un structured output (Pydantic model) o texto
```

**ToolResolver**: El módulo `tool_executor.py` implementa `ToolResolver`, que usa `MultiServerMCPClient` de [`langchain-mcp-adapters`](https://docs.langchain.com/oss/python/langchain/mcp) para conectar dinámicamente con MCP servers:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async with MultiServerMCPClient({
    "brave_search": {
        "url": settings.mcp_brave_search_url,
        "transport": "streamable_http",
    },
    "playwright": {
        "url": settings.mcp_playwright_url,
        "transport": "streamable_http",
    },
}) as client:
    mcp_tools = client.get_tools()
    all_tools = mcp_tools + [simple_scrape_url_tool]
```

**Structured output**: El ScraperAgent soporta dos modos de respuesta:
1. **Nativo** (`response_model`): pasa un modelo Pydantic directamente al LLM para structured output nativo
2. **Legacy** (`structured_output=True`): usa `OutputParser` para parsear la respuesta del LLM en un schema Pydantic

**Retry logic**: Detecta errores recuperables de red y reintenta automáticamente hasta 3 veces, reseteando la memoria del agente entre cada intento.

#### Archivos del módulo

| Archivo | Responsabilidad |
|---------|----------------|
| `agent.py` | Clase `ScraperAgent` — async context manager, ReAct loop, retry, structured output |
| `tool_executor.py` | `ToolResolver` — conecta con MCP servers via `MultiServerMCPClient` |
| `tools.py` | Tool `simple_scrape_url` — scraping HTTP directo con httpx |
| `prompts.py` | System prompts dinámicos construidos desde config.json |
| `config_schema.py` | Schemas Pydantic para validar `config.json` (`AgentConfig`, `CountryConfig`) |
| `output_parser.py` | `OutputParser` — parsea respuestas LLM en modelos Pydantic |
| `memory.py` | Checkpointer `InMemorySaver` para el ScraperAgent |

---

### 🔌 MCP Servers (Model Context Protocol)

**Ubicación**: `aifoundry/app/mcp_servers/externals/`

[MCP](https://modelcontextprotocol.io/) es un protocolo abierto que estandariza cómo las aplicaciones proporcionan herramientas y contexto a los LLMs. AIWorld usa MCP para desacoplar las herramientas externas de los agentes.

| Server | Puerto | Tools | Transporte |
|--------|--------|-------|------------|
| **Brave Search** | 8082 → 8080 | `brave_web_search` | `streamable_http` |
| **Playwright** | 8931 | `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, etc. | `streamable_http` |

Se conectan a los agentes via [`langchain-mcp-adapters`](https://docs.langchain.com/oss/python/langchain/mcp) usando `MultiServerMCPClient`.

---

### 🔥 Hefesto (Frontend)

**Ubicación**: `hefesto/`

Hefesto es la interfaz conversacional diseñada como **Tab App** para Microsoft Teams. Filosofía *chat-first*: el usuario escribe preguntas en lenguaje natural.

- **SSE Streaming**: `chatService.ts` usa `fetch()` con `ReadableStream` para parsear eventos SSE (no usa `EventSource` nativo)
- **Eventos soportados**: `thinking`, `tool_start`, `tool_end`, `token`, `error`, `end`
- **Rendering progresivo**: mensajes token a token; thinking/tool blocks expandibles
- **Teams integration**: `@microsoft/teams-js` SDK + `teams-manifest/manifest.json`
- **Dark theme**: interfaz oscura optimizada para Teams

---

### ⚡ LiteLLM Proxy

Proxy universal que permite conectar con cualquier proveedor LLM (OpenAI, Azure, Anthropic, etc.) usando API compatible OpenAI. Cambio de modelo sin tocar código — solo variables de entorno.

---

## Arquitectura Config-Driven

Cada dominio de scraping se configura declarativamente mediante `config.json`:

```json
{
  "product": "electricity_prices",
  "query_template": "electricity prices {country} {providers} current rates",
  "extraction_prompt": "Extract electricity pricing data...",
  "countries": {
    "ES": { "language": "Spanish", "providers": ["Iberdrola", "Endesa"] }
  }
}
```

Permite **añadir nuevos dominios sin escribir código** — solo creando un nuevo `config.json` y registrando el tool wrapper.

---

## Streaming SSE — Protocolo de Eventos

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `thinking` | El agente está razonando | `{ content: string }` |
| `tool_start` | Inicio de invocación de herramienta | `{ tool: string, input: object }` |
| `tool_end` | Resultado de herramienta | `{ tool: string, output: string }` |
| `token` | Token de respuesta parcial | `{ content: string }` |
| `error` | Error durante la ejecución | `{ message: string }` |
| `end` | Fin del stream | `{ thread_id: string }` |

---

## Estructura del Proyecto

```
AIWorld/
├── README.md                          # Este archivo
├── docker-compose.yml                 # MCP servers (Brave Search, Playwright)
├── pyproject.toml                     # Dependencias Python (uv/pip)
├── .env.example                       # Variables de entorno requeridas
├── aifoundry/                         # Backend (FastAPI)
│   ├── app/
│   │   ├── main.py                    # Entry point FastAPI + lifespan
│   │   ├── config.py                  # Settings (Pydantic BaseSettings)
│   │   ├── api/                       # router.py, chat_teams_router.py, schemas.py
│   │   ├── core/
│   │   │   ├── agenticai/deepagents/chat_teams/  # ChatTeamsAgent (Capa 2)
│   │   │   └── aiagents/scraper/                  # ScraperAgent (Capa 1)
│   │   ├── mcp_servers/externals/     # Brave Search + Playwright MCP
│   │   ├── schemas/                   # Response models (Pydantic)
│   │   └── utils/                     # country, parsing, rate_limiter, etc.
│   └── tests/                         # unit/ (14 archivos) + integration/
├── hefesto/                           # Frontend (React 19 + TypeScript + Vite)
│   ├── src/                           # App, hooks, services, components, types
│   └── teams-manifest/manifest.json   # Microsoft Teams Tab App manifest
├── docs/                              # AGENTS.md, MCP.md, HEFESTO_DESIGN.md, etc.
└── scripts/                           # Tests e2e y utilidades (start/stop)
```

---

## Quick Start

### Prerrequisitos

- **Python** ≥ 3.11, **Node.js** ≥ 18, **Docker** + Docker Compose, **uv** (recomendado)

### 1. Clonar y configurar

```bash
git clone https://github.com/sergiolrinditex/AIWorld.git
cd AIWorld
cp .env.example .env
# Editar .env con tus API keys (LITELLM_MODEL, LITELLM_BASE_URL, LITELLM_API_KEY, BRAVE_API_KEY)
```

### 2. Levantar MCP Servers

```bash
docker compose up -d
```

### 3. Instalar dependencias e iniciar backend

```bash
uv sync          # o: pip install -e .
uv run uvicorn aifoundry.app.main:app --reload --port 8000
```

### 4. Instalar e iniciar frontend

```bash
cd hefesto
npm install
cp .env.example .env.local
npm run dev      # → http://localhost:5173
```

### 5. Verificar

```bash
curl http://localhost:8000/api/health
# → {"status": "ok"}
```

---

## API Reference

### Chat Teams (SSE)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/chat` | Chat SSE streaming (eventos en tiempo real) |
| `POST` | `/api/chat/sync` | Chat síncrono (respuesta completa) |
| `GET` | `/api/chat/history/{thread_id}` | Historial de conversación por thread |

### Scraper Agents (REST)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/agents` | Lista agentes disponibles |
| `GET` | `/api/agents/{name}/config` | Configuración de un agente |
| `POST` | `/api/agents/{name}/run` | Ejecutar un agente |

---

## Dominios de Scraping

| Dominio | Config | Descripción |
|---------|--------|-------------|
| **Electricidad** | `electricity/config.json` | Precios de electricidad por país y proveedor |
| **Salarios** | `salary/config.json` | Salarios medios por país, sector y rol |
| **Comentarios sociales** | `social_comments/config.json` | Análisis de sentimiento en redes sociales |

---

## Tests

```bash
# Tests unitarios
uv run pytest aifoundry/tests/unit/ -v

# Tests de integración
uv run pytest aifoundry/tests/integration/ -v

# Tests end-to-end (requiere infra levantada)
python scripts/test_electricity_agent.py
python scripts/test_salary_agent.py
python scripts/test_social_comments_agent.py
python scripts/test_memory_multiturn.py
```

---

## Seguridad y Resiliencia

- **Rate limiting**: `rate_limiter.py` controla la frecuencia de llamadas a APIs externas
- **Retry con backoff**: ScraperAgent reintenta hasta 3 veces en errores recuperables
- **Context manager**: `async with ScraperAgent(...)` garantiza limpieza de recursos MCP
- **Validación Pydantic**: todos los inputs/outputs se validan con schemas tipados
- **Singleton thread-safe**: ChatTeamsAgent como instancia única con lazy init
- **Streaming resiliente**: errores durante el stream se emiten como evento `error` sin romper la conexión

---

## Observabilidad y Monitoreo

- **Logging estructurado**: `logging.getLogger(__name__)` en todos los módulos
- **AgentCallbackHandler**: registra cada paso del ScraperAgent (search, scrape, extraction)
- **Eventos SSE trazables**: cada evento incluye tipo, timestamp y datos para debugging
- **Health check**: `GET /api/health` para readiness probes

---

## Documentación Adicional

| Documento | Contenido |
|-----------|-----------|
| [`docs/AGENTS.md`](docs/AGENTS.md) | Guía completa de la taxonomía de agentes |
| [`docs/MCP.md`](docs/MCP.md) | Documentación de MCP servers y integración |
| [`docs/HEFESTO_DESIGN.md`](docs/HEFESTO_DESIGN.md) | Diseño de arquitectura del frontend |
| [`docs/LANGCHAIN_ECOSYSTEM_ANALYSIS.md`](docs/LANGCHAIN_ECOSYSTEM_ANALYSIS.md) | Análisis del ecosistema LangChain |
| [`hefesto/README.md`](hefesto/README.md) | README específico del frontend |

---

## Roadmap

- [ ] Persistencia de memoria en base de datos (LangGraph Store)
- [ ] Nuevos dominios de scraping (inmobiliario, empleo, etc.)
- [ ] Human-in-the-loop para validación de datos extraídos
- [ ] Dashboard de observabilidad con LangSmith
- [ ] Deployment en Kubernetes con Helm charts
- [ ] Soporte multi-idioma en la interfaz de Hefesto

---

## Contributing

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature/mi-feature`
3. Commit con mensaje descriptivo: `git commit -m "feat: descripción"`
4. Push y crear Pull Request

---

## Licencia

Proyecto interno de [Inditex / PeopleTech](https://www.inditex.com). Uso restringido.
