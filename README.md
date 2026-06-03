[![progress-banner](https://backend.codecrafters.io/progress/ai-agent/id/placeholder)](https://app.codecrafters.io/courses/ai-agent/overview)

This is a starting point for Python solutions to the
["Build Your Own AI Agent" Challenge](https://app.codecrafters.io/courses/ai-agent/overview).

In this challenge, you'll build an AI coding agent similar to Claude Code or Cursor Agent. Your agent will be able to use tools like reading/writing files, executing terminal commands, and more.

**Note**: Head over to [codecrafters.io](https://codecrafters.io) to try the challenge.

---

# AI Coding Agent

Agente de IA que ejecuta tareas de programación de forma autónoma usando el patrón **tool-use**: el LLM razona, invoca herramientas (leer/escribir archivos, ejecutar comandos) y repite hasta completar la tarea.

## Inicio rápido

```bash
# 1. Instalar dependencias
python -m venv .venv && source .venv/Scripts/activate
pip install -e ".[dev]"

# 2. Configurar API key
export OPENROUTER_API_KEY="sk-or-..."

# 3. Ejecutar
./your_program.sh -p "Lee README.md y resume su contenido"
```

## Configuración

| Variable | Default | Descripción |
|---|---|---|
| `OPENROUTER_API_KEY` | — | **Requerida**. API key de OpenRouter |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Endpoint compatible con OpenAI |
| `OPENROUTER_MODEL` | `openrouter/free` | Modelo a usar |
| `WORKSPACE_PATH` | `./workspace` | Directorio de trabajo del agente |

## Estructura del proyecto

```
app/
├── main.py                        # CLI entry point
├── agent.py                       # AgentLoop — ciclo principal
├── tool.py                        # Clases base Tool y ToolRegistry
├── tools.py                       # read_file, write_file, bash_terminal
└── providers/
    ├── base.py                    # LLMProvider abstracto + retry logic
    ├── openai_compat_provider.py  # Implementación OpenAI-compatible
    └── registry.py                # ProviderSpec y registro
docs/                              # Documentación detallada
tests/                             # Suite de tests (173 tests)
```

## Tools disponibles

| Tool | Descripción |
|---|---|
| `read_file` | Lee el contenido de un archivo |
| `write_file` | Escribe contenido a un archivo |
| `bash_terminal` | Ejecuta un comando bash y devuelve stdout |

## Tests

```bash
# Todos los tests (excluye live)
python -m pytest tests/ -v

# Con reporte de cobertura
python -m pytest tests/ --cov=app --cov-report=term-missing

# Tests live (requiere API key real)
RUN_LIVE_TESTS=1 python -m pytest tests/ -m live
```

## Documentación

| Documento | Contenido |
|---|---|
| [docs/introduccion.md](docs/introduccion.md) | Motivación, tecnologías y estructura del repositorio |
| [docs/agent-loop.md](docs/agent-loop.md) | Ciclo de razonamiento, flujo de ejecución y diagramas |
| [docs/providers.md](docs/providers.md) | Capa de proveedores LLM, retry logic y dataclasses |
| [docs/tools-basicas.md](docs/tools-basicas.md) | Referencia de tools y cómo crear tools personalizados |
| [docs/permisos.md](docs/permisos.md) | Variables de entorno, límites y consideraciones de seguridad |