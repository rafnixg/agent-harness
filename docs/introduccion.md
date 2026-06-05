# Introducción

**AI Coding Agent** es un agente de inteligencia artificial diseñado para ejecutar tareas de programación de forma autónoma. Combina un modelo de lenguaje (LLM) con un conjunto de herramientas que le permiten leer y escribir archivos, ejecutar comandos en terminal y razonar sobre el resultado de cada acción.

El proyecto nació como solución al challenge ["Build Your Own AI Agent"](https://app.codecrafters.io/courses/ai-agent/overview) de CodeCrafters y replica la mecánica principal de herramientas como Claude Code o Cursor Agent.

---

## Motivación

Los LLM modernos pueden razonar sobre código pero por sí solos no pueden actuar sobre un sistema de archivos real. El patrón **tool-use** (o function calling) soluciona esto: el modelo emite llamadas a funciones estructuradas y el agente las ejecuta, devolviendo el resultado como contexto para la siguiente iteración.

Este proyecto implementa ese ciclo de forma mínima y legible, sin frameworks externos.

---

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.11+ | Lenguaje principal |
| OpenAI SDK (v2) | Cliente HTTP para APIs compatibles con OpenAI |
| OpenRouter | Gateway para acceder a múltiples modelos (Claude, GPT, etc.) |
| loguru | Logging estructurado |
| json_repair | Tolerancia a JSON malformado en respuestas del LLM |
| pytest + pytest-asyncio | Suite de tests |

---

## Cómo empezar

### 1. Clonar e instalar dependencias

```bash
git clone <repo>
cd agent-harness
uv venv
uv sync --all-extras
```

### 2. Configurar variables de entorno

```bash
export OPENROUTER_API_KEY="sk-or-..."
export OPENROUTER_MODEL="anthropic/claude-haiku-4.5"   # opcional
export PERMISSION_POLICY="ask_once"                      # opcional
```

### 3. Ejecutar el agente

```bash
uv run -m app.main \
    -p "Lee el archivo README.md y resume su contenido" \
    --provider openrouter \
    --permission-policy allow_list \
    --allow-tools "read_file,write_file"
```

---

## Estructura del repositorio

```
app/
├── main.py                        # CLI entry point
├── agent.py                       # AgentLoop — ciclo principal
├── tool.py                        # Clases base Tool y ToolRegistry
├── tools.py                       # Implementaciones concretas (read, write, bash)
└── providers/
    ├── base.py                    # LLMProvider abstracto + retry
    ├── openai_compat_provider.py  # Proveedor OpenAI-compatible
    └── registry.py                # ProviderSpec y registro de proveedores
docs/
├── introduccion.md                # Este archivo
├── agent-loop.md                  # Ciclo de conversación
├── permisos.md                    # Variables de entorno y seguridad
├── providers.md                   # Capa de proveedores LLM
└── tools-basicas.md               # Herramientas disponibles
tests/                             # Suite de tests (pytest)
```

---

## Documentación

| Sección | Descripción |
|---|---|
| [Agent Loop](agent-loop.md) | Cómo funciona el ciclo de razonamiento, uso de providers y herramientas |
| [Providers](providers.md) | Integración con APIs de LLM compatibles con OpenAI |
| [Tools básicas](tools-basicas.md) | Referencia de `read_file`, `write_file`, `bash_terminal` y `PermissionPolicy` |
| [Permisos](permisos.md) | Variables de entorno, políticas de permiso, seguridad y límites de ejecución |
