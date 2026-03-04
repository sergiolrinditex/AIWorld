# 🔥 Hefesto — Diseño de Arquitectura

> **Hefesto** es el frontend conversacional de AIWorld para Microsoft Teams.
> Chat-first, powered by Deep Agents (LangChain), streaming SSE.

**Versión**: 2.0.0
**Última actualización**: Abril 2026
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
8. [Setup y Desarrollo](#setup-y-desarrollo)

---

## Visión General

### ❌ Lo que NO es Hefesto

- **NO** es un dashboard con formularios y dropdowns
- **NO** requiere que el usuario seleccione agente/país/proveedor manualmente
- **NO** tiene múltiples pantallas/wizard

### ✅ Lo que SÍ es Hefesto

- Un **chat conversacional** estilo ChatGPT
- El usuario escribe en **lenguaje natural**: _"¿Cuánto cobra un dependiente de Zara en España?"_
- El **ChatTeamsAgent** (Deep Agent) decide qué tools/sub-agentes usar
- Los resultados se muestran **inline en el chat** con Markdown
- Muestra **thinking blocks** y **tool calls** en tiempo real (streaming)

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│                 Microsoft Teams                          │
│                 (Tab App / iframe)                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                   HEFESTO                                 │
│              React + TypeScript + Vite                    │
│                  Puerto: 5173                             │
│                                                          │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ App.tsx  │  │ useChat()   │  │ chatService.ts     │  │
│  │          │──│ hook        │──│ SSE EventSource    │  │
│  └──────────┘  └─────────────┘  └─────────┬──────────┘  │
│                                            │             │
│  ┌──────────┐  ┌─────────────┐  ┌─────────┴──────────┐  │
│  │ChatInput │  │MessageList  │  │ MessageBubble      │  │
│  │          │  │             │  │ ThinkingBlock       │  │
│  │          │  │             │  │ ToolBlock           │  │
│  └──────────┘  └─────────────┘  └────────────────────┘  │
└──────────────────┬──────────────────────────────────────┘
                   │ POST /api/chat (SSE)
                   ▼
┌─────────────────────────────────────────────────────────┐
│                 AIFOUNDRY (Backend)                       │
│                 FastAPI · Puerto: 8000                    │
│                                                          │
│  chat_teams_router.py → ChatTeamsAgent (Deep Agent)      │
└─────────────────────────────────────────────────────────┘
```

---

## ChatTeamsAgent (Deep Agent)

El backend expone un **ChatTeamsAgent** construido con `deepagents.create_deep_agent()` de LangChain. Este agente:

1. **Recibe** mensajes en lenguaje natural del usuario
2. **Razona** qué herramientas necesita (Brave Search, ScraperAgents, Playwright)
3. **Ejecuta** las herramientas necesarias
4. **Streama** la respuesta token-a-token via SSE

### Tools disponibles

| Tool | Descripción |
|------|-------------|
| `search_electricity` | Busca precios de electricidad (ScraperAgent) |
| `search_salary` | Busca salarios (ScraperAgent) |
| `search_social_comments` | Busca comentarios sociales (ScraperAgent) |
| `list_available_agents` | Lista dominios disponibles |
| `brave_web_search` | Búsqueda web directa (MCP) |
| `playwright_*` | Navegación web (MCP) |

Ver [docs/AGENTS.md](AGENTS.md) para la documentación completa.

---

## API Contract (SSE Streaming)

### Endpoint principal

```
POST /api/chat
Content-Type: application/json
Accept: text/event-stream

{
  "message": "¿Cuánto cuesta la luz en España?",
  "thread_id": "optional-session-id"
}
```

### Eventos SSE

El servidor emite eventos Server-Sent Events con el siguiente formato:

```
event: <tipo>
data: <json>
```

| Evento | Data | Descripción |
|--------|------|-------------|
| `thinking` | `{"content": "..."}` | El agente está razonando internamente |
| `tool_start` | `{"tool": "nombre", "input": {...}}` | Inicio de llamada a herramienta |
| `tool_end` | `{"tool": "nombre", "output": "..."}` | Resultado de herramienta |
| `token` | `{"content": "..."}` | Token de respuesta final |
| `end` | `{"thread_id": "..."}` | Fin del stream |
| `error` | `{"message": "..."}` | Error durante la ejecución |

### Endpoints adicionales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/chat/sync` | Chat sincrónico (sin streaming) |
| `GET` | `/api/chat/history/{thread_id}` | Historial de conversación |

### Ejemplo de flujo SSE

```
→ POST /api/chat {"message": "precio luz España"}

← event: thinking
← data: {"content": "Voy a buscar información sobre precios de electricidad..."}

← event: tool_start
← data: {"tool": "search_electricity", "input": {"query": "precio luz", "country": "ES"}}

← event: tool_end
← data: {"tool": "search_electricity", "output": "Datos encontrados: ..."}

← event: token
← data: {"content": "Según"}

← event: token
← data: {"content": " los datos"}

← event: token
← data: {"content": " más recientes..."}

← event: end
← data: {"thread_id": "abc-123"}
```

---

## Frontend Components

### Estructura de archivos

```
hefesto/src/
├── App.tsx                    # Layout principal (header + chat area)
├── main.tsx                   # Entry point React (Teams init)
├── index.css                  # Estilos globales (Tailwind-like)
│
├── hooks/
│   └── useChat.ts             # Hook principal: SSE, state, messages
│
├── services/
│   └── chatService.ts         # Conexión SSE con el backend
│
├── types/
│   └── chat.ts                # Tipos TypeScript (ChatMessage, ChatEvent, etc.)
│
├── components/
│   ├── ChatInput.tsx           # Input de texto + botón enviar
│   ├── MessageList.tsx         # Lista scrollable de mensajes
│   ├── MessageBubble.tsx       # Burbuja individual (user/assistant)
│   ├── ThinkingBlock.tsx       # Bloque de "pensamiento" del agente
│   └── ToolBlock.tsx           # Bloque de tool call (expandible)
│
└── lib/
    └── teams.ts                # Wrapper Microsoft Teams SDK
```

### `useChat()` — Hook principal

El hook `useChat` es el corazón de la comunicación frontend-backend:

```typescript
const {
  messages,          // ChatMessage[]
  isLoading,         // boolean
  sendMessage,       // (text: string) => void
  threadId,          // string
} = useChat();
```

Internamente:
1. `sendMessage()` → llama a `chatService.sendChatMessage()`
2. `chatService` → abre una conexión SSE (`EventSource`)
3. Los eventos se procesan y actualizan `messages` en real-time
4. Los `thinking` events → `ThinkingBlock`
5. Los `tool_start/tool_end` events → `ToolBlock`
6. Los `token` events → se acumulan en el `MessageBubble` del assistant

### `App.tsx` — Layout principal

```
┌─────────────────────────────────────┐
│         Header (AIWorld)             │
├─────────────────────────────────────┤
│                                      │
│         MessageList                  │
│  ┌───────────────────────────────┐  │
│  │ User: "precio luz España"     │  │
│  ├───────────────────────────────┤  │
│  │ 🤔 ThinkingBlock             │  │
│  │ "Voy a buscar..."            │  │
│  ├───────────────────────────────┤  │
│  │ 🔧 ToolBlock                 │  │
│  │ search_electricity(...)       │  │
│  ├───────────────────────────────┤  │
│  │ Assistant: "Los precios..."   │  │
│  └───────────────────────────────┘  │
│                                      │
├─────────────────────────────────────┤
│         ChatInput                    │
│  [Escribe tu mensaje...] [Enviar]   │
└─────────────────────────────────────┘
```

### `MessageBubble` — Renderizado de mensajes

- Soporta **Markdown** via `react-markdown` + `remark-gfm`
- Diferencia visualmente mensajes de `user` vs `assistant`
- Muestra `ThinkingBlock` y `ToolBlock` inline

### `ThinkingBlock` — Bloques de pensamiento

Muestra el razonamiento interno del agente en un bloque colapsable/expandible con estilo diferenciado.

### `ToolBlock` — Llamadas a herramientas

Muestra las llamadas a tools del agente (nombre de la tool, input, output) en un formato expandible que permite ver los detalles.

---

## Integración Microsoft Teams

### Configuración

Hefesto se despliega como una **Tab App** dentro de Microsoft Teams:

- **SDK**: `@microsoft/teams-js` v2.49+
- **Init**: `teams.ts` → `app.initialize()` en `main.tsx`
- **Manifest**: `hefesto/teams-manifest/manifest.json`

### Flujo de inicialización

```typescript
// hefesto/src/lib/teams.ts
import { app } from "@microsoft/teams-js";

export async function initializeTeams(): Promise<boolean> {
  try {
    await app.initialize();
    return true;
  } catch {
    // No estamos en Teams, modo standalone
    return false;
  }
}
```

```typescript
// hefesto/src/main.tsx
initializeTeams().then(() => {
  createRoot(document.getElementById("root")!).render(<App />);
});
```

### Manifest (Teams App)

```json
// hefesto/teams-manifest/manifest.json
{
  "$schema": "...",
  "manifestVersion": "1.19",
  "id": "...",
  "name": { "short": "AIWorld" },
  "staticTabs": [{
    "entityId": "hefesto",
    "name": "AIWorld Chat",
    "contentUrl": "https://your-domain/hefesto",
    "scopes": ["personal"]
  }]
}
```

### Modo dual

Hefesto funciona tanto **dentro de Teams** como **standalone** en el navegador:
- Si `app.initialize()` tiene éxito → modo Teams (con Teams context)
- Si falla → modo standalone (funciona igual, sin Teams SDK features)

---

## Stack Tecnológico

| Tecnología | Versión | Uso |
|-----------|---------|-----|
| **React** | 19.x | UI framework |
| **TypeScript** | 5.9 | Tipado estático |
| **Vite** | 7.x | Build tool y dev server |
| **@microsoft/teams-js** | 2.49+ | Integración Microsoft Teams |
| **react-markdown** | 10.x | Renderizado de Markdown en mensajes |
| **remark-gfm** | 4.x | Soporte para tablas, links, etc. en Markdown |
| **lucide-react** | latest | Iconos |

### Configuración Vite

```typescript
// hefesto/vite.config.ts
export default defineConfig({
  plugins: [react()],
  envDir: '..',          // Lee .env desde la raíz del monorepo
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',  // Proxy al backend
    },
  },
});
```

El proxy en Vite redirige todas las peticiones `/api/*` al backend FastAPI en puerto 8000, evitando problemas de CORS en desarrollo.

---

## Setup y Desarrollo

### Prerrequisitos

- Node.js ≥ 18
- npm o pnpm

### Instalación

```bash
cd hefesto
npm install
```

### Desarrollo

```bash
npm run dev
# Hefesto arranca en http://localhost:5173
```

### Build para producción

```bash
npm run build
# Output en hefesto/dist/
```

### Variables de entorno

```bash
# hefesto/.env.example
VITE_API_BASE_URL=http://localhost:8000  # URL del backend
```

> **Nota**: Vite lee `.env` desde `envDir: '..'` (raíz del monorepo). Las variables para el frontend deben tener prefijo `VITE_`.

### Linting

```bash
npm run lint
```

---

<p align="center">
  <a href="../README.md">← Volver al README</a> · <a href="MCP.md">← MCP Servers</a> · <a href="LANGCHAIN_ECOSYSTEM_ANALYSIS.md">Ecosistema LangChain →</a>
</p>