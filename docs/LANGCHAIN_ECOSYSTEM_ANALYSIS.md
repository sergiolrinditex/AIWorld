# Análisis del Ecosistema LangChain vs. Los 4 Paradigmas de AI

> **Fecha**: Marzo 2026  
> **Objetivo**: Mapear los productos del ecosistema LangChain (LangChain, LangGraph, Deep Agents) a los 4 paradigmas de AI definidos en AIFoundry, y evaluar si encajan o si requieren definir un paradigma nuevo.

---

## 1. Resumen de los productos

### 🔗 LangChain (`langchain.com/langchain`)

**Qué es**: Framework open source con arquitectura de agentes pre-construida e integraciones para cualquier modelo o herramienta.

**Características clave**:
- `create_agent` proporciona un patrón ReAct probado sobre el runtime de LangGraph
- **1000+ integraciones** — intercambiar modelos, tools y bases de datos sin reescribir código (no vendor lock-in)
- Middleware extensible: human-in-the-loop, compresión de conversaciones, eliminación de datos sensibles
- Runtime durable (persistencia de estado)

**En esencia**: LangChain es la **capa de orquestación y abstracción** — el pegamento que conecta LLMs, tools, retrievers y memoria. No es un paradigma en sí mismo, sino la **librería base** que habilita todos los paradigmas.

---

### 🕸️ LangGraph (`langchain.com/langgraph`)

**Qué es**: Runtime de agentes y framework de orquestación de bajo nivel. *"Balance agent control with agency"*.

**Características clave**:
- **Human-in-the-loop**: Moderación y controles de calidad fáciles de añadir
- **Workflows expresivos**: Flujos de control personalizables — single agent, multi-agent, jerárquico
- **Primitivos de bajo nivel**: Flexibilidad total para crear agentes completamente customizados
- Soporte para grafos de estado con nodos, edges condicionales y checkpoints

**En esencia**: LangGraph es el **motor de ejecución** que permite construir desde un agente simple (AI Agent) hasta sistemas multi-agente complejos (Agentic AI). Es el runtime sobre el que se ejecutan los agentes.

---

### 🧠 Deep Agents (`langchain.com/deep-agents`)

**Qué es**: Harness open source de agentes construido para **tareas de larga duración**. Maneja planificación, gestión de contexto y orquestación multi-agente para trabajo complejo como investigación y programación.

**Características clave**:
- **Descomponer objetivos complejos**: Planning tools que permiten descomponer tareas, trackear progreso y adaptarse
- **Delegar trabajo en paralelo**: Spawn de sub-agentes para subtareas independientes, cada uno con contexto aislado
- **Filesystem como memoria**: Almacena system prompts, skills y memoria a largo plazo en el filesystem
- **Gestión nativa de contexto**: Compresión de historial, offload de resultados grandes, aislamiento de contexto entre sub-agentes, prompt caching
- **Model-neutral**: Cualquier proveedor de LLM, máxima configurabilidad
- **Arquitectura**: Deep Agents → LangGraph → LangChain → LLM + Tools + Planning Tool + Filesystem Tools + Sub-agents

**En esencia**: Deep Agents es la **implementación más avanzada del paradigma Agentic AI** — agentes autónomos de larga duración que planifican, delegan a sub-agentes y gestionan su propio contexto.

---

## 2. Mapeo a los 4 Paradigmas de AI

| Paradigma | Producto(s) | Encaja? | Explicación |
|-----------|-------------|---------|-------------|
| **LLM Workflow** | **LangChain** (LCEL chains) | ✅ Sí | LangChain permite crear pipelines/chains simples de LLM: prompt → LLM → output. Ideal para chatbots, generación de texto, resúmenes. |
| **RAG** | **LangChain** (retrievers + vector stores) | ✅ Sí | LangChain incluye todas las primitivas RAG: Document Loaders, Text Splitters, Embeddings, Vector Stores, Retrievers. Es el ecosistema más maduro para RAG. |
| **AI Agent** | **LangChain** (`create_agent`) + **LangGraph** (runtime) | ✅ Sí | LangChain expone `create_agent` que proporciona un patrón ReAct probado. Por debajo usa **LangGraph** como runtime durable con grafos de estado, checkpoints y human-in-the-loop. **Es lo que AIFoundry usa hoy.** |
| **Agentic AI** | **LangGraph** (multi-agent) + **Deep Agents** | ✅ Sí | LangGraph soporta arquitecturas multi-agent y jerárquicas. Deep Agents lleva esto al máximo con sub-agentes autónomos, planificación y memoria a largo plazo. |

### Relación entre productos

> **Importante**: LangChain y LangGraph no son alternativas — son capas complementarias. `create_agent` de LangChain usa LangGraph como runtime por debajo. La diferencia es el nivel de abstracción:

| Nivel | Producto | Para qué |
|-------|----------|----------|
| **Alto nivel** | **LangChain** (`create_agent`) | Crear un agente ReAct rápido con configuración mínima |
| **Bajo nivel** | **LangGraph** (grafos de estado) | Control total: diseñar flujos custom, multi-agent, jerárquicos |
| **Máxima autonomía** | **Deep Agents** (harness) | Agentes de larga duración con planning, sub-agentes y memoria |

### Diagrama de capas

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

---

## 3. Conclusión: ¿Paradigma nuevo?

**No se necesita un paradigma nuevo.** Los 3 productos del ecosistema LangChain encajan perfectamente dentro de los 4 paradigmas ya definidos:

| Capa del stack | Paradigma(s) que habilita | Producto |
|----------------|---------------------------|----------|
| Librería base + alto nivel | LLM Workflow + RAG + AI Agent (`create_agent`) | LangChain |
| Runtime de agentes (bajo nivel) | AI Agent + Agentic AI (grafos custom, multi-agent) | LangGraph |
| Harness autónomo | Agentic AI (máxima expresión) | Deep Agents |

### Deep Agents ≈ Agentic AI en su máxima expresión

Deep Agents no introduce un paradigma nuevo — es la **implementación de referencia del paradigma Agentic AI** que ya teníamos definido. Lo que aporta es:

1. **Planning nativo** — Los agentes descomponen tareas complejas automáticamente
2. **Sub-agentes con contexto aislado** — Cada sub-agente tiene su propio contexto, evitando contaminación
3. **Memoria a largo plazo via filesystem** — Skills y conocimiento persisten entre ejecuciones
4. **Gestión de contexto** — Compresión, caching y offloading para tareas de larga duración

Esto es exactamente lo que describíamos como *"Sistema multi-agente autónomo — Tareas a gran escala que requieren colaboración"* en nuestra tabla.

---

## 4. Impacto en AIFoundry — Roadmap tecnológico

### Hoy: AI Agent con LangGraph ✅
```
AIFoundry → LangGraph (ReAct) → LangChain → LiteLLM → Bedrock/Claude
```

### Próximo: RAG con LangChain
```
AIFoundry → LangChain Retrievers → Vector DB → Documents
```

### Futuro: Agentic AI con Deep Agents
```
AIFoundry → Deep Agents → LangGraph → LangChain → Multi-agent orchestration
```

### Stack propuesto por paradigma

| Paradigma | Tecnología propuesta | Estado |
|-----------|---------------------|--------|
| **LLM Workflow** | LangChain LCEL chains | 🔲 Pendiente |
| **RAG** | LangChain + ChromaDB/Pinecone | 🔲 Pendiente |
| **AI Agent** | LangGraph + ScraperAgent | ✅ Implementado |
| **Agentic AI** | Deep Agents + LangGraph multi-agent | 🔲 Pendiente |

---

## 5. Ejemplos concretos de evolución

### Ejemplo: De AI Agent a Agentic AI (Salarios)

**Hoy (AI Agent)**:
```
Usuario → ScraperAgent → [Brave Search + Playwright] → SalaryResponse
```
Un único agente hace toda la investigación.

**Futuro (Agentic AI con Deep Agents)**:
```
Usuario → PlanningAgent
            ├── ResearchAgent → [Brave Search] → datos brutos de salarios
            ├── ScrapingAgent → [Playwright] → datos de portales específicos
            ├── ValidationAgent → [Cross-reference] → verificación de datos
            └── SynthesisAgent → SalaryResponse (consolidado y verificado)
```
Múltiples agentes especializados colaborando, cada uno con su contexto aislado.

---

## Referencias

- [LangChain](https://www.langchain.com/langchain) — Framework open source con 1000+ integraciones
- [LangGraph](https://www.langchain.com/langgraph) — Runtime de agentes con orquestación de bajo nivel
- [Deep Agents](https://www.langchain.com/deep-agents) — Harness de agentes para tareas complejas de larga duración
- [LangSmith](https://www.langchain.com/langsmith) — Plataforma de observabilidad y deployment