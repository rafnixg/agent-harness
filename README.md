# AI Coding Agent Harness

Agente de IA que ejecuta tareas de programación de forma autónoma usando el patrón **tool-use**: el LLM razona, invoca herramientas (leer/escribir archivos, ejecutar comandos) y repite hasta completar la tarea.

## Inicio rápido

```bash
# 1. Instalar dependencias
uv venv
uv sync --all-extras

# 2. Configurar credenciales (ejemplo OpenRouter)
export OPENROUTER_API_KEY="sk-or-..."

# 3. Ejecutar
uv run -m app.main -p "Lee README.md y resume su contenido"
```

## Configuración

| Variable | Default | Descripción |
|---|---|---|
| `OPENROUTER_API_KEY` | — | API key para provider `openrouter` |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Endpoint compatible con OpenAI |
| `OPENROUTER_MODEL` | `openrouter/free` | Modelo a usar |
| `LLM_PROVIDER` | `openrouter` | Provider a usar (`openrouter`, `openai`, `anthropic`, etc.) |
| `LLM_MODEL` | — | Modelo por defecto alternativo (si no se define `OPENROUTER_MODEL`) |
| `WORKSPACE_PATH` | `./workspace` | Directorio de trabajo del agente |
| `PERMISSION_POLICY` | `always_ask` | Política de permisos (`always_ask`, `always_allow`, `ask_once`, `allow_list`) |
| `PERMISSION_ALLOWLIST` | `""` | Lista de tools separadas por coma (solo para `allow_list`) |

## CLI

```bash
uv run -m app.main \
    -p "Busca TODOs en el repo" \
    --provider openrouter \
    --model openrouter/free \
    --workspace ./workspace \
    --permission-policy allow_list \
    --allow-tools "read_file,write_file"
```

Opciones principales:

- `-p` prompt de entrada (requerido)
- `--provider` provider definido en `app/providers/registry.py`
- `--model` modelo para el provider
- `--workspace` workspace del agente
- `--permission-policy` control de ejecución de tools
- `--allow-tools` allowlist para `allow_list`

## Políticas de permisos

| Política | Comportamiento |
|---|---|
| `always_ask` | Pregunta en cada tool call |
| `always_allow` | Ejecuta sin preguntar |
| `ask_once` | Pregunta la primera vez por cada tool y recuerda la decisión en la sesión |
| `allow_list` | Auto-autoriza tools permitidas y pregunta las demás |

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
| [docs/agent-loop.md](docs/agent-loop.md) | Ciclo de razonamiento, soporte multi-provider y ejecución de tools |
| [docs/providers.md](docs/providers.md) | Capa de proveedores LLM, retry logic y dataclasses |
| [docs/tools-basicas.md](docs/tools-basicas.md) | Referencia de tools, registry y políticas de permiso |
| [docs/permisos.md](docs/permisos.md) | Variables de entorno, políticas de permiso y seguridad |