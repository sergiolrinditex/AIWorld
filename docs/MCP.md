# 🔌 MCP Servers — Model Context Protocol

> Documentación de los servidores MCP que proporcionan herramientas externas a los agentes de AIWorld.

**Versión**: 2.0.0
**Última actualización**: Abril 2026

---

## 📖 Índice

1. [¿Qué es MCP?](#qué-es-mcp)
2. [Arquitectura](#arquitectura)
3. [Brave Search MCP](#brave-search-mcp)
4. [Playwright MCP](#playwright-mcp)
5. [Integración con LangChain](#integración-con-langchain)
6. [Docker Compose](#docker-compose)
7. [Configuración](#configuración)
8. [Añadir un Nuevo MCP Server](#añadir-un-nuevo-mcp-server)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## ¿Qué es MCP?

**Model Context Protocol (MCP)** es un protocolo estándar para que los modelos de IA se conecten con herramientas y fuentes de datos externas. En AIWorld, los MCP servers exponen capacidades de búsqueda web y navegación a los agentes.

```
┌──────────────────┐     streamable_http     ┌──────────────────┐
│   ScraperAgent   │ ◄─────────────────────► │  Brave Search    │
│   ChatTeamsAgent │                          │  MCP Server      │
│                  │     streamable_http     ┌──────────────────┐
│                  │ ◄─────────────────────► │  Playwright      │
│                  │                          │  MCP Server      │
└──────────────────┘                          └──────────────────┘
```

---

## Arquitectura

### Estructura de archivos

```
aifoundry/app/mcp_servers/
├── __init__.py
└── externals/
    ├── __init__.py
    ├── brave_search/
    │   ├── __init__.py
    │   ├── brave_search_mcp.py    # Configuración MCP (get_mcp_config)
    │   └── Dockerfile             # Imagen Docker del servidor
    └── playwright/
        ├── __init__.py
        ├── playwright_mcp.py      # Configuración MCP (get_mcp_config)
        └── Dockerfile             # Imagen Docker del servidor
```

### Transporte

Ambos servidores usan **`streamable_http`** como protocolo de transporte — HTTP estándar con streaming bidireccional. Esto permite comunicación eficiente sin necesidad de WebSockets.

---

## Brave Search MCP

### Descripción

Servidor MCP que expone la API de [Brave Search](https://brave.com/search/api/) como herramienta para los agentes. Permite búsquedas web programáticas con filtros de frescura, idioma y región.

### Configuración

| Variable | Valor | Descripción |
|----------|-------|-------------|
| Puerto host | `8082` | Puerto expuesto en el host |
| Puerto container | `8080` | Puerto interno del container |
| Transporte | `streamable_http` | Protocolo de comunicación |
| URL MCP | `http://localhost:8082/mcp` | Endpoint para los agentes |

### Variables de entorno requeridas

```bash
BRAVE_API_KEY=your-brave-api-key    # API key de Brave Search
MCP_BRAVE_SEARCH_URL=http://localhost:8082/mcp  # URL del servidor
```

### Herramientas expuestas

| Herramienta | Descripción |
|-------------|-------------|
| `brave_web_search` | Búsqueda web con query, freshness, count, country |

### Dockerfile

```dockerfile
# Basado en Node.js - instala @anthropic-ai/mcp-server-brave-search
# Configurable via variables de entorno
```

### Configuración Python

```python
# aifoundry/app/mcp_servers/externals/brave_search/brave_search_mcp.py

def get_mcp_config() -> dict:
    return {
        "brave-search": {
            "url": settings.mcp_brave_search_url,  # http://localhost:8082/mcp
            "transport": "streamable_http",
        }
    }
```

---

## Playwright MCP

### Descripción

Servidor MCP que expone [Playwright](https://playwright.dev/) como herramientas de navegación web para los agentes. Permite navegar páginas, hacer click, extraer texto, tomar screenshots, y más — todo en un Chromium headless dentro de Docker.

### Configuración

| Variable | Valor | Descripción |
|----------|-------|-------------|
| Puerto host | `8931` | Puerto expuesto en el host |
| Puerto container | `8931` | Puerto interno del container |
| Transporte | `streamable_http` | Protocolo de comunicación |
| URL MCP | `http://localhost:8931/mcp` | Endpoint para los agentes |

### Variables de entorno requeridas

```bash
MCP_PLAYWRIGHT_URL=http://localhost:8931/mcp  # URL del servidor
```

### Herramientas expuestas

| Herramienta | Descripción |
|-------------|-------------|
| `browser_navigate` | Navegar a una URL |
| `browser_click` | Click en un elemento |
| `browser_type` | Escribir texto en un input |
| `browser_snapshot` | Capturar el DOM accesible |
| `browser_screenshot` | Capturar screenshot |
| `browser_go_back` | Navegar atrás |
| `browser_go_forward` | Navegar adelante |
| `browser_wait` | Esperar un tiempo |
| `browser_close` | Cerrar el navegador |

### Dockerfile

```dockerfile
# Basado en Node.js + Chromium
# Ejecuta: npx @playwright/mcp@latest --port 8931 --host 0.0.0.0
# Con --executable-path al chromium instalado en la imagen
```

### Configuración Python

```python
# aifoundry/app/mcp_servers/externals/playwright/playwright_mcp.py

def get_mcp_config() -> dict:
    return {
        "playwright": {
            "url": settings.mcp_playwright_url,  # http://localhost:8931/mcp
            "transport": "streamable_http",
        }
    }
```

---

## Integración con LangChain

Los servidores MCP se integran con LangChain via `langchain-mcp-adapters`, que convierte las herramientas MCP en tools compatibles con LangChain/LangGraph.

### ToolResolver

```python
# aifoundry/app/core/aiagents/scraper/tool_executor.py

class ToolResolver:
    """Carga tools locales + MCP tools."""

    async def get_tools(self) -> list[BaseTool]:
        local_tools = [simple_scrape_url]

        # Cargar MCP tools
        mcp_configs = self._get_mcp_configs()
        async with MultiServerMCPClient(mcp_configs) as client:
            mcp_tools = client.get_tools()

        return local_tools + mcp_tools

    def _get_mcp_configs(self) -> dict:
        """Combina configs de todos los MCP servers."""
        configs = {}
        configs.update(brave_search_mcp.get_mcp_config())
        configs.update(playwright_mcp.get_mcp_config())
        return configs
```

### MultiServerMCPClient

La clase `MultiServerMCPClient` de `langchain-mcp-adapters` gestiona:
- Conexión a múltiples MCP servers simultáneamente
- Descubrimiento de herramientas disponibles
- Conversión de tools MCP → LangChain tools
- Manejo de errores (con `_tool_error_handler` configurado)

---

## Docker Compose

Ambos MCP servers se definen en `docker-compose.yml` en la raíz del proyecto:

```yaml
services:
  brave-search-mcp:
    build:
      context: .
      dockerfile: aifoundry/app/mcp_servers/externals/brave_search/Dockerfile
    container_name: aifoundry_brave_search_mcp
    restart: unless-stopped
    env_file: [.env]
    environment:
      - PORT=8080
      - BRAVE_MCP_TRANSPORT=http
      - BRAVE_MCP_PORT=8080
      - BRAVE_MCP_HOST=0.0.0.0
    ports: ["8082:8080"]
    networks: [aifoundry_network]

  playwright-mcp:
    build:
      context: .
      dockerfile: aifoundry/app/mcp_servers/externals/playwright/Dockerfile
    container_name: aifoundry_playwright_mcp
    restart: unless-stopped
    env_file: [.env]
    environment:
      - PORT=8931
    ports: ["8931:8931"]
    networks: [aifoundry_network]
    command: npx -y @playwright/mcp@latest --port 8931 --host 0.0.0.0 ...

networks:
  aifoundry_network:
    driver: bridge
```

### Comandos Docker

```bash
# Levantar ambos MCP servers
docker compose up -d

# Ver estado
docker compose ps

# Ver logs de un server específico
docker logs aifoundry_brave_search_mcp
docker logs aifoundry_playwright_mcp

# Reconstruir imágenes
docker compose build

# Parar todo
docker compose down
```

---

## Configuración

### Variables de entorno (.env)

```bash
# Brave Search
BRAVE_API_KEY=your-brave-api-key

# MCP Server URLs
MCP_BRAVE_SEARCH_URL=http://localhost:8082/mcp
MCP_PLAYWRIGHT_URL=http://localhost:8931/mcp
```

### Configuración en el backend (config.py)

```python
# aifoundry/app/config.py
class Settings(BaseSettings):
    # MCP Servers
    mcp_brave_search_url: str = "http://localhost:8082/mcp"
    mcp_playwright_url: str = "http://localhost:8931/mcp"
```

---

## Añadir un Nuevo MCP Server

### Paso 1: Crear estructura de archivos

```bash
mkdir -p aifoundry/app/mcp_servers/externals/mi_server/
```

### Paso 2: Crear el archivo de configuración

```python
# aifoundry/app/mcp_servers/externals/mi_server/mi_server_mcp.py

from aifoundry.app.config import settings

def get_mcp_config() -> dict:
    return {
        "mi-server": {
            "url": settings.mcp_mi_server_url,
            "transport": "streamable_http",
        }
    }
```

### Paso 3: Crear el Dockerfile

```dockerfile
# aifoundry/app/mcp_servers/externals/mi_server/Dockerfile
FROM node:20-slim
# Instalar tu MCP server
RUN npm install -g @tu-org/mcp-server-mi-tool
EXPOSE 8XXX
CMD ["npx", "@tu-org/mcp-server-mi-tool", "--port", "8XXX"]
```

### Paso 4: Añadir al docker-compose.yml

```yaml
  mi-server-mcp:
    build:
      context: .
      dockerfile: aifoundry/app/mcp_servers/externals/mi_server/Dockerfile
    container_name: aifoundry_mi_server_mcp
    restart: unless-stopped
    ports: ["8XXX:8XXX"]
    networks: [aifoundry_network]
```

### Paso 5: Registrar en ToolResolver

```python
# En tool_executor.py, añadir a _get_mcp_configs():
from aifoundry.app.mcp_servers.externals.mi_server import mi_server_mcp

configs.update(mi_server_mcp.get_mcp_config())
```

### Paso 6: Añadir variable de entorno

```bash
# .env
MCP_MI_SERVER_URL=http://localhost:8XXX/mcp
```

```python
# config.py
mcp_mi_server_url: str = "http://localhost:8XXX/mcp"
```

---

## Testing

### Scripts de test

```bash
# Test Brave Search MCP
python scripts/test_brave_mcp.py

# Test Playwright MCP
python scripts/test_playwright_mcp.py
```

### Test manual con curl

```bash
# Verificar que Brave Search MCP está respondiendo
curl http://localhost:8082/mcp

# Verificar que Playwright MCP está respondiendo
curl http://localhost:8931/mcp
```

### Test desde Python

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def test_mcp():
    config = {
        "brave-search": {
            "url": "http://localhost:8082/mcp",
            "transport": "streamable_http",
        }
    }
    async with MultiServerMCPClient(config) as client:
        tools = client.get_tools()
        print(f"Tools disponibles: {[t.name for t in tools]}")

asyncio.run(test_mcp())
```

---

## Troubleshooting

### MCP server no arranca

1. **Verificar Docker**: `docker compose ps` — ¿el container está running?
2. **Ver logs**: `docker logs aifoundry_brave_search_mcp` o `docker logs aifoundry_playwright_mcp`
3. **Puerto en uso**: verificar que los puertos 8082 y 8931 no están ocupados

### Error "Connection refused"

1. Los MCP servers tardan unos segundos en arrancar tras `docker compose up`
2. Verificar la URL: debe incluir `/mcp` al final (ej: `http://localhost:8082/mcp`)
3. Si usas Docker Desktop, asegurar que los puertos están mapeados correctamente

### Brave Search no devuelve resultados

1. Verificar `BRAVE_API_KEY` en `.env`
2. La API key debe ser válida y tener cuota disponible
3. Probar directamente: `python scripts/test_brave_mcp.py`

### Playwright timeout

1. El container necesita Chromium — verificar que la imagen Docker lo incluye
2. Incrementar timeout si las páginas son pesadas
3. Verificar que `NODE_TLS_REJECT_UNAUTHORIZED=0` está configurado (para HTTPS)

### Error "Tool not found"

1. El `MultiServerMCPClient` descubre tools dinámicamente — verificar que el server devuelve tools
2. Revisar que `get_mcp_config()` devuelve la URL correcta
3. Las tools MCP se configuran con `_tool_error_handler` para evitar crashes en errores

---

<p align="center">
  <a href="../README.md">← Volver al README</a> · <a href="AGENTS.md">← Agentes</a> · <a href="HEFESTO_DESIGN.md">Hefesto →</a>
</p>