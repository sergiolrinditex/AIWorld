# 🔥 Hefesto — Diseño de Arquitectura

> **Hefesto** es el frontend conversacional de AIWorld para Microsoft Teams.
> Chat-first, powered by Deep Agents (LangChain), streaming SSE.

**Versión**: 2.0.0
**Fecha**: Marzo 2026
**Equipo**: Inditex / PeopleTech / AIWorld

---

## 📖 Índice

1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [ChatTeamsAgent (Deep Agent)](#chatteamsagent-deep-agent)
4. [API Contract (SSE Streaming)](#api-contract-sse-streaming)
5. [Frontend Components](#frontend-components)
6. [Integración Microsoft Teams](#integración-microsoft-teams)
7. [Stack Tecnológico](#stack-tecnológico)

---

## Visión General

### ❌ Lo que NO es Hefesto

- **NO** es un dashboard con formularios y dropdowns
- **NO** requiere que el usuario seleccione agente/país/proveedor manualmente
- **NO** tiene múltiples pantallas/wizard

### ✅ Lo que SÍ es Hefesto

- Un **chat conversacional** estilo Cline/ChatGPT
- El usuario escribe en **lenguaje natural**: _"¿Cuánto cobra un dependiente de Zara en España?"_
- El **ChatTeamsAgent** (Deep Agent) decide qué tools/sub-agentes usar
- Los resultados se muestran inline con **tool blocks visibles** (transparencia del proceso)
- **Streaming en tiempo real** vía SSE (Server-Sent Events)

### Flujo de Ejemplo

```
Usuario: "Dame los precios de electricidad de Endesa en España"

Hefesto:
  🧠 Thinking: Analizando la consulta... necesito buscar precios de electricidad.
  🔧 Tool: search_electricity(provider="Endesa", country_code="ES")
     ├─ 🔍 Brave Search: "precio electricidad Endesa España marzo 2026"
     ├─ 📄 Scraping: endesa.com/tarifas
     └─ ✅ Datos extraídos

  📊 Resultado:
  Las tarifas actuales de Endesa en España son:
  - Tarifa One Luz: 0.156 €/kWh (fija)
  - Tarifa Tempo: 0.12-0.19 €/kWh (3 períodos)
  Fuente: endesa.com (consultado 03/03/2026)
```

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Microsoft Teams                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  Hefesto (React)                       │  │
│  │  ┌─────────┐  ┌──────────────┐  ┌────────────────┐   │  │
│  │  │ ChatInput│  │ MessageList  │  │  Sidebar       │   │  │
│  │  └────┬────┘  │ ├ ChatMessage│  │  ├ Historial   │   │  │
│  │       │       │ ├ ToolBlock  │  │  ├ Settings    │   │  │
│  │       │       │ ├ ThinkBlock │  │  └ Info        │   │  │
│  │       │       │ └ StreamText │  └────────────────┘   │  │
│  │       │       └──────┬───────┘                        │  │
│  └───────┼──────────────┼────────────────────────────────┘  │
│          │     SSE      │                                    │
└──────────┼──────────────┼────────────────────────────────────┘
           │              │
    ┌──────▼──────────────▼──────────────────────────────┐
    │              FastAPI Backend                         │
    │  ┌──────────────────────────────────────────────┐   │
    │  │         POST /api/chat (SSE)                  │   │
    │  │         GET  /api/chat/history/{id}           │   │
    │  │         DELETE /api/chat/history/{id}         │   │
    │  └──────────────────┬───────────────────────────┘   │
    │                     │                                │
    │  ┌──────────────────▼───────────────────────────┐   │
    │  │          ChatTeamsAgent (Deep Agent)           │   │
    │  │  ┌─────────────────────────────────────────┐  │   │
    │  │  │ Tools:                                   │  │   │
    │  │  │  • search_electricity → ScraperAgent     │  │   │
    │  │  │  • search_salary → ScraperAgent          │  │   │
    │  │  │  • search_social → ScraperAgent          │  │   │
    │  │  │  • MCP: Bing, Jira, Confluence, etc.     │  │   │
    │  │  └─────────────────────────────────────────┘  │   │
    │  └───────────────────────────────────────────────┘   │
    └──────────────────────────────────────────────────────┘
```

### Capas

| Capa | Tecnología | Responsabilidad |
|------|-----------|-----------------|
| **Presentación** | React + TypeScript + Vite | UI chat, rendering de mensajes y tool blocks |
| **Transporte** | SSE (Server-Sent Events) | Streaming bidireccional de eventos |
| **API** | FastAPI | Endpoints REST + SSE, autenticación |
| **Orquestación** | ChatTeamsAgent (Deep Agent) | Routing de intenciones, delegación a sub-agentes |
| **Ejecución** | ScraperAgent (ReAct) | Web scraping con Brave Search + Playwright |
| **Datos** | MCP Servers | Bing, Fabric, SharePoint, Jira, Confluence |

---

## ChatTeamsAgent (Deep Agent)

### ¿Por qué Deep Agent?

| Característica | ReACT(`create_agent`) | Deep Agent (`deepagents`) |
|---------------|---------------------|--------------------------|
| Sub-agent spawning | ❌ Manual | ✅ Nativo |
| Long-term memory | ❌ Solo checkpoints | ✅ Persistente |
| Context compression | ❌ | ✅ Automático |
| Streaming events | ⚠️ Básico | ✅ Rico (thinking, tools, text) |
| Ideal para | Agentes simples (ScraperAgent) | Agentes conversacionales complejos |

### Estructura de Archivos

```
core/agenticai/deepagents/chat_teams/
├── __init__.py          # Exports públicos
├── agent.py             # ChatTeamsAgent — Deep Agent principal
├── config.py            # Configuración del agente
├── prompts.py           # System prompt de Hefesto
├── tools.py             # Tools que wrappean ScraperAgents
├── memory.py            # Configuración de memoria persistente
└── streaming.py         # Event iterator para SSE
```

### System Prompt (Hefesto)

```
Eres Hefesto, el asistente de IA de PeopleTech (Inditex).
Tu misión es ayudar a los equipos de People & Technology a obtener
información sobre precios de electricidad, salarios y menciones
en redes sociales.

Cuando el usuario haga una consulta:
1. Analiza qué tipo de información necesita
2. Usa las tools disponibles para buscar datos actualizados
3. Presenta los resultados de forma clara y estructurada
4. Cita siempre las fuentes con URLs

Tools disponibles:
- search_electricity: Buscar precios de electricidad por proveedor y país
- search_salary: Buscar datos salariales por empresa y país
- search_social: Buscar menciones en redes sociales por persona y red social
```

### Tools del ChatTeamsAgent

| Tool | Descripción | Parámetros |
|------|------------|------------|
| `search_electricity` | Busca precios/tarifas de electricidad | `provider`, `country_code` |
| `search_salary` | Busca datos salariales del retail/moda | `provider`, `country_code` |
| `search_social` | Busca menciones en redes sociales | `person_name`, `social_network`, `country_code` |

Cada tool internamente crea un `ScraperAgent`, le pasa el config correspondiente, y devuelve los resultados.

---

## API Contract (SSE Streaming)

### `POST /api/chat`

**Request:**
```json
{
  "message": "Dame los precios de electricidad de Endesa en España",
  "thread_id": "optional-uuid"
}
```

**Response:** `text/event-stream` (SSE)

```
event: thinking
data: {"content": "Analizando la consulta... necesito buscar precios de electricidad."}

event: tool_start
data: {"tool": "search_electricity", "params": {"provider": "Endesa", "country_code": "ES"}}

event: tool_result
data: {"tool": "search_electricity", "status": "success", "result": "...datos..."}

event: text
data: {"content": "Las tarifas actuales de Endesa"}

event: text
data: {"content": " en España son:\n- Tarifa One Luz..."}

event: done
data: {"thread_id": "abc-123", "total_steps": 3}
```

### Event Types

| Evento | Descripción | Campos |
|--------|------------|--------|
| `thinking` | El agente está razonando | `content` |
| `tool_start` | Inicio de ejecución de tool | `tool`, `params` |
| `tool_result` | Resultado de tool | `tool`, `status`, `result` |
| `text` | Fragmento de texto de respuesta | `content` |
| `error` | Error durante la ejecución | `message`, `code` |
| `done` | Fin del stream | `thread_id`, `total_steps` |

### `GET /api/chat/history/{thread_id}`

**Response:**
```json
{
  "thread_id": "abc-123",
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "...", "tools_used": [...]}
  ]
}
```

### `DELETE /api/chat/history/{thread_id}`

**Response:**
```json
{
  "status": "deleted",
  "thread_id": "abc-123"
}
```

---

## Frontend Components

### Árbol de Componentes

```
App
├── AppLayout
│   ├── Sidebar
│   │   ├── ConversationList
│   │   ├── NewChatButton
│   │   └── AppInfo
│   └── ChatPanel
│       ├── ChatHeader
│       ├── MessageList
│       │   ├── ChatMessage (role=user)
│       │   └── ChatMessage (role=assistant)
│       │       ├── ThinkingBlock
│       │       ├── ToolBlock
│       │       │   ├── ToolHeader (nombre + estado)
│       │       │   ├── ToolParams (parámetros colapsables)
│       │       │   └── ToolResult (resultado colapsable)
│       │       └── StreamingText
│       └── ChatInput
│           ├── TextArea (auto-resize)
│           └── SendButton
```

### Componentes Clave

#### `ChatMessage`
- Renderiza mensajes de usuario y asistente
- Para mensajes del asistente, parsea y renderiza tool blocks inline
- Soporte para Markdown en las respuestas

#### `ToolBlock` (estilo Cline)
- **Header**: Icono + nombre del tool + estado (running/success/error)
- **Params**: Parámetros enviados (colapsable, mostrado por defecto)
- **Result**: Resultado obtenido (colapsable, mostrado al completar)
- **Estados visuales**: 
  - 🔄 Running: spinner + borde azul
  - ✅ Success: check + borde verde
  - ❌ Error: x + borde rojo

#### `ThinkingBlock`
- Fondo suave (gris/lavanda)
- Colapsable (expandido por defecto durante streaming)
- Icono de cerebro 🧠

#### `StreamingText`
- Texto que aparece progresivamente (caracter a caracter o token a token)
- Cursor parpadeante al final durante streaming
- Renderizado Markdown completo al finalizar

#### `ChatInput`
- TextArea con auto-resize
- Enviar con Enter (Shift+Enter para nueva línea)
- Botón de enviar deshabilitado durante streaming
- Placeholder: _"Pregunta a Hefesto..."_

---

## Integración Microsoft Teams

### Teams Tab App

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.17/MicrosoftTeams.schema.json",
  "manifestVersion": "1.17",
  "id": "hefesto-peopletech",
  "name": { "short": "Hefesto", "full": "Hefesto - PeopleTech AI Assistant" },
  "description": {
    "short": "AI assistant for PeopleTech",
    "full": "Chat with Hefesto to find electricity prices, salaries, and social mentions"
  },
  "staticTabs": [{
    "entityId": "hefesto-chat",
    "name": "Chat",
    "contentUrl": "https://{host}/hefesto",
    "scopes": ["personal"]
  }]
}
```

### Teams SDK Integration

- `@microsoft/teams-js` para detección de contexto Teams
- Adaptación automática de tema (light/dark/high-contrast)
- SSO via `authentication.getAuthToken()` (futuro)
- Funciona también standalone fuera de Teams (modo desarrollo)

---

## Stack Tecnológico

### Backend

| Librería | Versión | Uso |
|----------|---------|-----|
| FastAPI | ≥0.115 | API REST + SSE |
| LangChain | ≥0.3.25 | Framework base |
| LangGraph | ≥0.4.1 | Orquestación de agentes |
| deepagents | latest | Deep Agent (`create_deep_agent`) para ChatTeamsAgent |
| langchain-openai | ≥0.3.18 | Azure OpenAI LLM |
| langchain-mcp-adapters | ≥0.1.2 | Conexión a MCP servers |

### Frontend

| Librería | Uso |
|----------|-----|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool |
| @microsoft/teams-js | Teams SDK |
| react-markdown | Rendering Markdown |
| remark-gfm | GitHub Flavored Markdown |
| lucide-react | Iconos |

### Comunicación

| Protocolo | Uso |
|-----------|-----|
| SSE (Server-Sent Events) | Streaming de eventos del agente al frontend |
| REST (JSON) | Historial, health check |
| MCP (Model Context Protocol) | Backend ↔ Tool servers |