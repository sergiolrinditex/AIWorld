#!/usr/bin/env bash
# ===========================================
# Setup Claude Code - Configuración automática
# ===========================================
# Este script lee las variables de .env del proyecto
# y configura Claude Code tanto para CLI como para
# la extensión de VS Code (anthropic.claude-code).
#
# Configura:
#   1. Variables de entorno desde .env
#   2. Claude Code CLI (npm global)
#   3. Variables de entorno en el shell profile
#   4. ~/.claude/settings.json (compartido CLI + extensión) - SIN mcpServers
#   5. Extensión VS Code (anthropic.claude-code)
#   6. VS Code User Settings para Claude Code
#   7. .vscode/settings.json del proyecto
#   8. MCP servers (limpieza previa + configuración via CLI)
#
# IMPORTANTE sobre MCP:
#   - Los MCP servers se configuran SOLO via `claude mcp add` CLI
#   - El CLI escribe el .mcp.json del proyecto en formato correcto
#   - NO se ponen mcpServers en ~/.claude/settings.json (causa conflictos)
#   - Antes de añadir, se borran las entradas previas para evitar duplicados
#
# Uso: ./scripts/setup_claude_code.sh
# ===========================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"
CLAUDE_SETTINGS_DIR="${HOME}/.claude"
CLAUDE_SETTINGS_FILE="${CLAUDE_SETTINGS_DIR}/settings.json"
VSCODE_PROJECT_DIR="${PROJECT_DIR}/.vscode"
VSCODE_PROJECT_SETTINGS="${VSCODE_PROJECT_DIR}/settings.json"
MCP_JSON="${PROJECT_DIR}/.mcp.json"

# -------------------------------------------
# Detección automática del sistema operativo
# -------------------------------------------
detect_os() {
    case "$(uname -s)" in
        Darwin*)  echo "macos" ;;
        Linux*)   echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

OS_TYPE="$(detect_os)"

# -------------------------------------------
# Detección automática del shell profile
# -------------------------------------------
detect_shell_profile() {
    local shell_name
    shell_name="$(basename "${SHELL:-/bin/bash}")"
    
    case "$shell_name" in
        zsh)
            if [[ -f "${HOME}/.zshrc" ]]; then
                echo "${HOME}/.zshrc"
            else
                echo "${HOME}/.zprofile"
            fi
            ;;
        bash)
            if [[ -f "${HOME}/.bashrc" ]]; then
                echo "${HOME}/.bashrc"
            elif [[ -f "${HOME}/.bash_profile" ]]; then
                echo "${HOME}/.bash_profile"
            else
                echo "${HOME}/.profile"
            fi
            ;;
        fish)
            echo "${HOME}/.config/fish/config.fish"
            ;;
        *)
            # Fallback
            if [[ -f "${HOME}/.bashrc" ]]; then
                echo "${HOME}/.bashrc"
            else
                echo "${HOME}/.profile"
            fi
            ;;
    esac
}

SHELL_PROFILE="$(detect_shell_profile)"

# -------------------------------------------
# Detección automática de ruta VS Code User Settings
# -------------------------------------------
detect_vscode_settings() {
    case "$OS_TYPE" in
        macos)
            echo "${HOME}/Library/Application Support/Code/User/settings.json"
            ;;
        linux)
            echo "${HOME}/.config/Code/User/settings.json"
            ;;
        windows)
            # Git Bash / MSYS2 / Cygwin
            echo "${APPDATA:-${HOME}/AppData/Roaming}/Code/User/settings.json"
            ;;
        *)
            # Fallback: intenta Linux primero, luego macOS
            if [[ -d "${HOME}/.config/Code" ]]; then
                echo "${HOME}/.config/Code/User/settings.json"
            elif [[ -d "${HOME}/Library/Application Support/Code" ]]; then
                echo "${HOME}/Library/Application Support/Code/User/settings.json"
            else
                echo "${HOME}/.config/Code/User/settings.json"
            fi
            ;;
    esac
}

VSCODE_USER_SETTINGS="$(detect_vscode_settings)"

# Tecla modificadora según OS (para la ayuda)
if [[ "$OS_TYPE" == "macos" ]]; then
    MOD_KEY="Cmd"
    MOD_KEY_ALT="Option"
else
    MOD_KEY="Ctrl"
    MOD_KEY_ALT="Alt"
fi

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}ℹ ${NC} $1"; }
success() { echo -e "${GREEN}✔ ${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠ ${NC} $1"; }
error()   { echo -e "${RED}✖ ${NC} $1"; }
section() { echo -e "\n${CYAN}━━━ $1 ━━━${NC}\n"; }

echo ""
echo "==========================================="
echo "  Claude Code - Setup para Inditex/LiteLLM"
echo "  (CLI + Extensión VS Code)"
echo "==========================================="
echo ""
info "🖥️  OS detectado: $OS_TYPE | Shell: $(basename "${SHELL:-bash}") | Profile: $SHELL_PROFILE"
info "📂 VS Code settings: $VSCODE_USER_SETTINGS"
echo ""

# -------------------------------------------
# 1. Verificar que existe el fichero .env
# -------------------------------------------
section "1/8 · Verificar fichero .env"

if [[ ! -f "$ENV_FILE" ]]; then
    error "No se encontró el fichero .env en: $ENV_FILE"
    error "Copia .env.example a .env y rellena los valores."
    exit 1
fi
success "Fichero .env encontrado: $ENV_FILE"

# -------------------------------------------
# 2. Leer variables de .env
# -------------------------------------------
section "2/8 · Leer variables de entorno"

get_env_var() {
    local var_name="$1"
    local value
    value=$(grep -E "^${var_name}=" "$ENV_FILE" | head -1 | cut -d'=' -f2-)
    # Eliminar comillas si las hay
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    echo "$value"
}

LITELLM_API_BASE=$(get_env_var "LITELLM_API_BASE")
LITELLM_API_KEY=$(get_env_var "LITELLM_API_KEY")
LITELLM_MODEL=$(get_env_var "LITELLM_MODEL")

if [[ -z "$LITELLM_API_BASE" ]]; then
    error "LITELLM_API_BASE no está definida en .env"
    exit 1
fi

if [[ -z "$LITELLM_API_KEY" ]]; then
    error "LITELLM_API_KEY no está definida en .env"
    exit 1
fi

if [[ -z "$LITELLM_MODEL" ]]; then
    warn "LITELLM_MODEL no está definida en .env, usando 'bedrock/claude-sonnet-4' por defecto"
    LITELLM_MODEL="bedrock/claude-sonnet-4"
fi

success "Variables leídas del .env:"
info "  ANTHROPIC_BASE_URL = $LITELLM_API_BASE"
info "  ANTHROPIC_AUTH_TOKEN = ${LITELLM_API_KEY:0:10}..."
info "  Model = $LITELLM_MODEL"

# -------------------------------------------
# 3. Verificar/Instalar Claude Code CLI
# -------------------------------------------
section "3/8 · Verificar Claude Code CLI"

if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "desconocida")
    success "Claude Code CLI encontrado (versión: $CLAUDE_VERSION)"
else
    warn "Claude Code CLI no encontrado. Instalando..."
    npm install -g @anthropic-ai/claude-code
    if command -v claude &> /dev/null; then
        success "Claude Code CLI instalado correctamente"
    else
        error "No se pudo instalar Claude Code CLI"
        error "Ejecuta manualmente: npm install -g @anthropic-ai/claude-code"
        exit 1
    fi
fi

# -------------------------------------------
# 4. Configurar variables de entorno en shell profile
# -------------------------------------------
section "4/8 · Configurar shell profile ($SHELL_PROFILE)"

# Marcador para identificar el bloque de Claude Code
MARKER_START="# >>> Claude Code Configuration (auto-generated) >>>"
MARKER_END="# <<< Claude Code Configuration <<<"

# Bloque de configuración
CONFIG_BLOCK="$MARKER_START
export ANTHROPIC_AUTH_TOKEN=\"${LITELLM_API_KEY}\"
export ANTHROPIC_BASE_URL=\"${LITELLM_API_BASE}\"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
$MARKER_END"

# Verificar si ya existe el bloque y reemplazarlo, o añadirlo
if grep -q "$MARKER_START" "$SHELL_PROFILE" 2>/dev/null; then
    # Eliminar bloque existente y reemplazar
    TEMP_FILE=$(mktemp)
    awk "/$MARKER_START/{skip=1} /$MARKER_END/{skip=0; next} !skip" "$SHELL_PROFILE" > "$TEMP_FILE"
    mv "$TEMP_FILE" "$SHELL_PROFILE"
    echo "" >> "$SHELL_PROFILE"
    echo "$CONFIG_BLOCK" >> "$SHELL_PROFILE"
    success "Bloque de configuración actualizado en $SHELL_PROFILE"
else
    echo "" >> "$SHELL_PROFILE"
    echo "$CONFIG_BLOCK" >> "$SHELL_PROFILE"
    success "Bloque de configuración añadido a $SHELL_PROFILE"
fi

# Exportar para la sesión actual
export ANTHROPIC_AUTH_TOKEN="$LITELLM_API_KEY"
export ANTHROPIC_BASE_URL="$LITELLM_API_BASE"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
success "Variables exportadas en la sesión actual"

# -------------------------------------------
# 5. Crear/actualizar ~/.claude/settings.json
#    IMPORTANTE: NO incluir mcpServers aquí.
#    Los MCP se gestionan SOLO via `claude mcp add`
#    que escribe al .mcp.json del proyecto.
# -------------------------------------------
section "5/8 · Configurar ~/.claude/settings.json (sin MCP)"

mkdir -p "$CLAUDE_SETTINGS_DIR"

# Si existe un settings.json previo con mcpServers, limpiar
if [[ -f "$CLAUDE_SETTINGS_FILE" ]]; then
    if command -v jq &> /dev/null; then
        # Verificar si tiene mcpServers y eliminarlo
        if jq -e '.mcpServers' "$CLAUDE_SETTINGS_FILE" &>/dev/null; then
            warn "Encontrado 'mcpServers' en ~/.claude/settings.json — eliminando para evitar conflictos"
            TEMP_SETTINGS=$(mktemp)
            jq 'del(.mcpServers)' "$CLAUDE_SETTINGS_FILE" > "$TEMP_SETTINGS" 2>/dev/null
            if [[ $? -eq 0 && -s "$TEMP_SETTINGS" ]]; then
                mv "$TEMP_SETTINGS" "$CLAUDE_SETTINGS_FILE"
                success "Eliminado mcpServers de ~/.claude/settings.json"
            else
                rm -f "$TEMP_SETTINGS"
                warn "No se pudo limpiar mcpServers con jq, se reescribirá el fichero"
            fi
        fi
    fi
fi

# Settings compartidos entre CLI y extensión VS Code
# NOTA: mcpServers se gestiona aparte via `claude mcp add` → escribe a .mcp.json
cat > "$CLAUDE_SETTINGS_FILE" << EOF
{
  "\$schema": "https://json.schemastore.org/claude-code-settings.json",
  "model": "${LITELLM_MODEL}",
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "${LITELLM_API_KEY}",
    "ANTHROPIC_BASE_URL": "${LITELLM_API_BASE}",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "${LITELLM_MODEL}",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "${LITELLM_MODEL}",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "${LITELLM_MODEL}",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
    "DISABLE_PROMPT_CACHING": "1"
  },
  "permissions": {
    "allow": [
      "Bash(npm:*)",
      "Bash(node:*)",
      "Bash(python:*)",
      "Bash(pip:*)",
      "Bash(git:*)",
      "Bash(cat:*)",
      "Bash(ls:*)",
      "Bash(find:*)",
      "Bash(grep:*)"
    ]
  }
}
EOF

success "Fichero creado/actualizado: $CLAUDE_SETTINGS_FILE"
info "  (Sin mcpServers — se gestionan via 'claude mcp add' → .mcp.json)"

# -------------------------------------------
# 6. Instalar y configurar extensión VS Code
# -------------------------------------------
section "6/8 · Extensión VS Code (anthropic.claude-code)"

# Verificar que 'code' CLI está disponible
if command -v code &> /dev/null; then
    # Verificar si la extensión ya está instalada
    if code --list-extensions 2>/dev/null | grep -qi "anthropic.claude-code"; then
        success "Extensión anthropic.claude-code ya instalada en VS Code"
    else
        info "Instalando extensión anthropic.claude-code en VS Code..."
        if code --install-extension anthropic.claude-code --force 2>/dev/null; then
            success "Extensión anthropic.claude-code instalada correctamente"
        else
            warn "No se pudo instalar la extensión automáticamente."
            warn "Instálala manualmente: ${MOD_KEY}+Shift+X → buscar 'Claude Code' → Install"
        fi
    fi

    # Configurar VS Code User Settings para Claude Code
    info "Configurando VS Code User Settings para Claude Code..."

    if [[ -f "$VSCODE_USER_SETTINGS" ]]; then
        if command -v jq &> /dev/null; then
            TEMP_SETTINGS=$(mktemp)
            jq --arg model "$LITELLM_MODEL" '
              . +
              {
                "claudeCode.disableLoginPrompt": true,
                "claudeCode.preferredLocation": "panel",
                "claudeCode.selectedModel": $model,
                "claudeCode.environmentVariables": [
                  "ANTHROPIC_AUTH_TOKEN",
                  "ANTHROPIC_BASE_URL",
                  "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS",
                  "DISABLE_PROMPT_CACHING"
                ]
              }
            ' "$VSCODE_USER_SETTINGS" > "$TEMP_SETTINGS" 2>/dev/null

            if [[ $? -eq 0 && -s "$TEMP_SETTINGS" ]]; then
                mv "$TEMP_SETTINGS" "$VSCODE_USER_SETTINGS"
                success "VS Code User Settings actualizado con configuración de Claude Code"
            else
                rm -f "$TEMP_SETTINGS"
                warn "No se pudo actualizar VS Code settings automáticamente con jq"
            fi
        elif command -v python3 &> /dev/null; then
            python3 << PYEOF
import json, sys

settings_path = "$VSCODE_USER_SETTINGS"
try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)
except:
    settings = {}

settings["claudeCode.disableLoginPrompt"] = True
settings["claudeCode.preferredLocation"] = "panel"
settings["claudeCode.selectedModel"] = "$LITELLM_MODEL"
settings["claudeCode.environmentVariables"] = [
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS",
    "DISABLE_PROMPT_CACHING"
]

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=4)
    f.write('\n')

print("OK")
PYEOF
            if [[ $? -eq 0 ]]; then
                success "VS Code User Settings actualizado con configuración de Claude Code"
            else
                warn "No se pudo actualizar VS Code settings automáticamente"
            fi
        else
            warn "No se encontró jq ni python3 para actualizar VS Code settings"
            warn "Añade manualmente a VS Code settings (${MOD_KEY}+,):"
            echo '    "claudeCode.disableLoginPrompt": true'
            echo '    "claudeCode.preferredLocation": "panel"'
            echo "    \"claudeCode.selectedModel\": \"$LITELLM_MODEL\""
        fi
    else
        # Crear el fichero de settings si no existe
        mkdir -p "$(dirname "$VSCODE_USER_SETTINGS")"
        cat > "$VSCODE_USER_SETTINGS" << EOF
{
    "claudeCode.disableLoginPrompt": true,
    "claudeCode.preferredLocation": "panel",
    "claudeCode.selectedModel": "${LITELLM_MODEL}",
    "claudeCode.environmentVariables": [
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS",
        "DISABLE_PROMPT_CACHING"
    ]
}
EOF
        success "VS Code User Settings creado con configuración de Claude Code"
    fi

    info "  Settings de VS Code configurados:"
    info "    claudeCode.disableLoginPrompt = true"
    info "    claudeCode.preferredLocation  = panel"
    info "    claudeCode.selectedModel      = $LITELLM_MODEL"
    info "    claudeCode.environmentVariables = [ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL, ...]"

else
    warn "Comando 'code' no encontrado en PATH."
    warn "Para habilitarlo: VS Code → ${MOD_KEY}+Shift+P → 'Shell Command: Install code command in PATH'"
    warn "Luego vuelve a ejecutar este script."
    echo ""
    warn "O instala la extensión manualmente:"
    info "  1. Abre VS Code"
    info "  2. ${MOD_KEY}+Shift+X → buscar 'Claude Code' → Install"
    info "  3. Ve a Settings (${MOD_KEY}+,) y configura:"
    echo '     "claudeCode.disableLoginPrompt": true'
    echo '     "claudeCode.preferredLocation": "panel"'
    echo "     \"claudeCode.selectedModel\": \"$LITELLM_MODEL\""
fi

# -------------------------------------------
# 7. Crear .vscode/settings.json del proyecto
# -------------------------------------------
section "7/8 · Configurar .vscode/settings.json del proyecto"

mkdir -p "$VSCODE_PROJECT_DIR"

if [[ -f "$VSCODE_PROJECT_SETTINGS" ]]; then
    # Actualizar settings existentes
    if command -v jq &> /dev/null; then
        TEMP_SETTINGS=$(mktemp)
        jq '
          . +
          {
            "claudeCode.preferredLocation": "panel",
            "claudeCode.autosave": true,
            "claudeCode.respectGitIgnore": true
          }
        ' "$VSCODE_PROJECT_SETTINGS" > "$TEMP_SETTINGS" 2>/dev/null

        if [[ $? -eq 0 && -s "$TEMP_SETTINGS" ]]; then
            mv "$TEMP_SETTINGS" "$VSCODE_PROJECT_SETTINGS"
            success ".vscode/settings.json actualizado"
        else
            rm -f "$TEMP_SETTINGS"
            warn "No se pudo actualizar .vscode/settings.json con jq, creando nuevo..."
        fi
    elif command -v python3 &> /dev/null; then
        python3 << PYEOF
import json

settings_path = "$VSCODE_PROJECT_SETTINGS"
try:
    with open(settings_path, 'r') as f:
        settings = json.load(f)
except:
    settings = {}

settings["claudeCode.preferredLocation"] = "panel"
settings["claudeCode.autosave"] = True
settings["claudeCode.respectGitIgnore"] = True

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=4)
    f.write('\n')
PYEOF
        success ".vscode/settings.json actualizado"
    fi
else
    cat > "$VSCODE_PROJECT_SETTINGS" << EOF
{
    "claudeCode.preferredLocation": "panel",
    "claudeCode.autosave": true,
    "claudeCode.respectGitIgnore": true
}
EOF
    success ".vscode/settings.json creado"
fi

# -------------------------------------------
# 8. Configurar MCP Servers
#    ESTRATEGIA: 
#    1. Borrar TODAS las conexiones MCP previas (local, project, user)
#    2. Borrar .mcp.json manual si existe
#    3. Usar SOLO `claude mcp add --scope project` que escribe .mcp.json correctamente
#    4. El formato que escribe el CLI es el que la extensión VS Code espera
# -------------------------------------------
section "8/8 · Configurar MCP Servers (limpieza + configuración)"

if command -v claude &> /dev/null; then
    # ── Paso 1: Borrar TODAS las conexiones MCP existentes ──
    info "Limpiando todas las conexiones MCP existentes..."
    
    # Obtener lista de MCP servers actuales y borrarlos uno a uno
    # Intentar borrar el servidor conocido en todos los scopes
    for scope in local project user; do
        claude mcp remove docs-langchain --scope "$scope" 2>/dev/null && \
            info "  Eliminado docs-langchain (scope: $scope)" || true
    done
    
    # También intentar borrar cualquier otro nombre que pueda existir
    for server_name in langchain-docs langchain docs; do
        for scope in local project user; do
            claude mcp remove "$server_name" --scope "$scope" 2>/dev/null || true
        done
    done
    
    success "Conexiones MCP previas limpiadas"
    
    # ── Paso 2: Eliminar .mcp.json manual previo ──
    # Lo borramos porque vamos a dejar que el CLI lo regenere
    if [[ -f "$MCP_JSON" ]]; then
        info "Eliminando .mcp.json manual previo (será regenerado por el CLI)..."
        rm -f "$MCP_JSON"
        success ".mcp.json eliminado"
    fi
    
    # ── Paso 3: Añadir MCP servers via CLI (scope project → escribe .mcp.json) ──
    info "Añadiendo MCP servers via CLI (scope: project)..."
    echo ""
    
    # docs-langchain: Documentación de LangChain via HTTP
    info "  Añadiendo docs-langchain (https://docs.langchain.com/mcp)..."
    if claude mcp add --transport http --scope project docs-langchain https://docs.langchain.com/mcp 2>&1; then
        success "  docs-langchain añadido correctamente (scope: project → .mcp.json)"
    else
        warn "  No se pudo añadir docs-langchain via CLI"
        warn "  Creando .mcp.json manualmente como fallback..."
        # Fallback: crear .mcp.json manualmente con el formato correcto
        cat > "$MCP_JSON" << 'MCPEOF'
{
  "mcpServers": {
    "docs-langchain": {
      "type": "http",
      "url": "https://docs.langchain.com/mcp"
    }
  }
}
MCPEOF
        success "  .mcp.json creado manualmente (fallback)"
    fi
    
    echo ""
    
    # ── Paso 4: Verificar estado final ──
    info "Estado final de MCP servers:"
    claude mcp list 2>&1 | sed 's/^/    /' || info "  (no se pudo listar)"
    
    echo ""
    if [[ -f "$MCP_JSON" ]]; then
        info "Contenido de .mcp.json:"
        cat "$MCP_JSON" | sed 's/^/    /'
    fi

else
    warn "Claude Code CLI no disponible. No se pueden configurar MCP servers via CLI."
    warn "Creando .mcp.json manualmente..."
    
    # Si no hay CLI, crear el fichero manualmente
    cat > "$MCP_JSON" << 'MCPEOF'
{
  "mcpServers": {
    "docs-langchain": {
      "type": "http",
      "url": "https://docs.langchain.com/mcp"
    }
  }
}
MCPEOF
    success ".mcp.json creado manualmente"
    warn "Para una configuración completa, instala Claude Code CLI y vuelve a ejecutar el script."
fi

# Asegurar que .vscode/ está en .gitignore (contiene settings locales)
if [[ -f "${PROJECT_DIR}/.gitignore" ]]; then
    if ! grep -q "^\.vscode/" "${PROJECT_DIR}/.gitignore" 2>/dev/null; then
        echo "" >> "${PROJECT_DIR}/.gitignore"
        echo "# VS Code local settings" >> "${PROJECT_DIR}/.gitignore"
        echo ".vscode/" >> "${PROJECT_DIR}/.gitignore"
        success ".vscode/ añadido a .gitignore"
    else
        info ".vscode/ ya está en .gitignore"
    fi
fi

# -------------------------------------------
# Resumen final
# -------------------------------------------
echo ""
echo "==========================================="
echo "  ✅ Configuración completada"
echo "==========================================="
echo ""
info "📁 Ficheros configurados:"
info "   Shell profile:           $SHELL_PROFILE"
info "   Claude Code settings:    $CLAUDE_SETTINGS_FILE (sin mcpServers)"
info "   VS Code User Settings:   $VSCODE_USER_SETTINGS"
info "   VS Code Project Settings: $VSCODE_PROJECT_SETTINGS"
info "   MCP config (proyecto):   $MCP_JSON (generado por CLI)"
echo ""
info "🔧 Modelo configurado: $LITELLM_MODEL"
info "🌐 API Base: $LITELLM_API_BASE"
echo ""
info "📋 Notas sobre MCP:"
info "   • MCP servers se configuran SOLO en .mcp.json (scope: project)"
info "   • NO se ponen en ~/.claude/settings.json (causa conflictos con VS Code)"
info "   • Usa 'claude mcp add/remove --scope project' para gestionar servers"
info "   • La extensión VS Code lee .mcp.json automáticamente"
echo ""
warn "IMPORTANTE: Recarga tu shell y VS Code para aplicar los cambios:"
echo ""
echo "    source $SHELL_PROFILE"
echo "    # En VS Code: ${MOD_KEY}+Shift+P → 'Developer: Reload Window'"
echo ""
echo "-------------------------------------------"
echo "  Cómo usar Claude Code:"
echo "-------------------------------------------"
echo ""
echo "  🖥️  EN VS CODE (Extensión):"
echo "    • Click en el icono ✱ de la barra de estado (abajo-derecha)"
echo "    • O ${MOD_KEY}+Shift+P → 'Claude Code: Open in New Tab'"
echo "    • O click en el icono Spark ✱ en la barra del editor"
echo ""
echo "  ⌨️  Atajos en VS Code:"
echo "    • ${MOD_KEY}+Esc        → Alternar foco entre editor y Claude"
echo "    • ${MOD_KEY}+Shift+Esc  → Abrir Claude en nueva pestaña"
echo "    • ${MOD_KEY}+N           → Nueva conversación (con Claude enfocado)"
echo "    • ${MOD_KEY_ALT}+K        → Insertar @-mención del fichero actual"
echo ""
echo "  💻 EN TERMINAL (CLI):"
echo "    • claude              → Iniciar Claude Code"
echo "    • claude --resume     → Reanudar conversación anterior"
echo "    • claude --version    → Ver versión instalada"
echo "    • /status             → (dentro de claude) Ver estado"
echo "    • /model              → (dentro de claude) Cambiar modelo"
echo "    • /mcp                → (dentro de claude) Ver/gestionar MCP servers"
echo ""
echo "  🔌 Gestión MCP:"
echo "    • claude mcp list                    → Listar servers"
echo "    • claude mcp add --transport http \\  → Añadir server HTTP"
echo "        --scope project <name> <url>"
echo "    • claude mcp remove <name>           → Eliminar server"
echo "    • /mcp                               → (dentro de claude) Estado MCP"
echo ""
echo "  📎 Tips:"
echo "    • Usa @fichero.ts para referenciar archivos"
echo "    • Usa @src/carpeta/ para referenciar directorios"
echo "    • Selecciona texto + ${MOD_KEY_ALT}+K para insertar referencia"
echo "    • Escribe / en el prompt para ver comandos disponibles"
echo ""