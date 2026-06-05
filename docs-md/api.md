# API HTTP

La API expone el agente por HTTP usando FastAPI.

## Endpoints

### GET /health

Verifica que el servicio este levantado.

Respuesta:

```json
{"status": "ok"}
```

### POST /ask

Ejecuta una consulta al agente y devuelve su respuesta final.

Request body:

```json
{
  "prompt": "Lee README.md y dame un resumen corto",
  "provider": "openrouter",
  "model": "openrouter/free",
  "workspace": "./workspace",
  "permission_policy": "always_ask",
  "allow_tools": "read_file"
}
```

Campos:

| Campo | Requerido | Default | Descripcion |
|---|---|---|---|
| `prompt` | Si | - | Pregunta/instruccion para el agente |
| `provider` | No | `LLM_PROVIDER` o `openrouter` | Provider definido en el registro |
| `model` | No | `OPENROUTER_MODEL` o `LLM_MODEL` o `openrouter/free` | Modelo a usar |
| `workspace` | No | `WORKSPACE_PATH` o `./workspace` | Directorio de trabajo para tools |
| `permission_policy` | No | `PERMISSION_POLICY` o `always_ask` | Politica de permisos |
| `allow_tools` | No | `PERMISSION_ALLOWLIST` o `""` | Lista separada por coma para `allow_list` |

Respuesta exitosa:

```json
{
  "result": "Resumen del archivo..."
}
```

Errores:

- `400`: configuracion invalida (por ejemplo provider desconocido o API key faltante)
- `500`: error interno no controlado

## Ejecucion local

```bash
uv run -m app.server --host 127.0.0.1 --port 8000
```

## Ejemplos con curl

```bash
curl http://127.0.0.1:8000/health
```

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Revisa README.md",
    "permission_policy": "allow_list",
    "allow_tools": "read_file"
  }'
```
