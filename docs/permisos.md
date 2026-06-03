# Permisos y configuración

Este documento cubre las variables de entorno que controlan el comportamiento del agente, los límites de seguridad integrados y las consideraciones de seguridad relevantes.

---

## Variables de entorno

### Requeridas

| Variable | Descripción |
|---|---|
| `OPENROUTER_API_KEY` | API key de [OpenRouter](https://openrouter.ai). El agente lanza `RuntimeError` si no está definida. |

### Opcionales

| Variable | Default | Descripción |
|---|---|---|
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | URL base del endpoint compatible con OpenAI. Puede apuntarse a cualquier API local (LM Studio, Ollama, etc.) |
| `OPENROUTER_MODEL` | `openrouter/free` | Identificador del modelo a usar. Ejemplos: `anthropic/claude-haiku-4.5`, `openai/gpt-4o-mini` |
| `WORKSPACE_PATH` | `./workspace` | Ruta raíz del directorio de trabajo del agente. |

### Ejemplo de `.env`

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=anthropic/claude-haiku-4.5
WORKSPACE_PATH=/home/user/projects/mi-proyecto
```

---

## Límites de ejecución

### Iteraciones del loop (`max_iterations`)

```python
AgentLoop(max_iterations=40)   # default
```

El agente ejecuta **máximo 40 ciclos** de razonamiento antes de lanzar `RuntimeError`. Esto previene bucles infinitos cuando el LLM no converge a una respuesta final.

Para tareas complejas que requieren muchos pasos, aumentar el valor:

```python
agent = AgentLoop(llm_provider=client, workspace=path, max_iterations=100)
```

### Tokens por respuesta (`max_tokens`)

```python
AgentLoop(max_tokens=4000)   # default
```

Limita el tamaño de cada respuesta del LLM. Reducirlo disminuye costos; aumentarlo permite respuestas más largas (útil para generación de código extenso).

### Reintentos del proveedor (`_CHAT_RETRY_DELAYS`)

La clase `LLMProvider` reintenta automáticamente en errores transitorios con backoff exponencial:

| Intento | Espera |
|---|---|
| 1° reintento | 1 s |
| 2° reintento | 2 s |
| 3° reintento | 4 s |
| Agotado | propaga la excepción |

Errores que activan reintento: `429`, `rate limit`, `500`, `502`, `503`, `504`, `overloaded`, `timeout`, `connection`, `server error`, `temporarily unavailable`.

---

## Consideraciones de seguridad

### `BashTerminalTool` — ejecución de comandos

La herramienta `bash_terminal` ejecuta comandos con `subprocess.run(..., shell=True)`. Esto implica:

- **Sin sandbox**: el agente tiene los mismos permisos que el proceso Python.
- **Sin lista blanca de comandos**: el LLM puede proponer cualquier comando.
- **Riesgo en entornos compartidos**: no exponer el agente como servicio público sin sandboxing adicional (Docker, firejail, etc.).

Recomendaciones:

- Ejecutar el agente con un usuario de bajos privilegios.
- Limitar `WORKSPACE_PATH` a un directorio específico.
- Considerar reemplazar `BashTerminalTool` por una versión con lista blanca en producción.

### `WriteFileTool` — escritura de archivos

Escribe a cualquier ruta del sistema de archivos. Si el agente es instruido por un prompt malicioso, podría sobrescribir archivos críticos.

Recomendación: validar que `file_path` esté dentro de `WORKSPACE_PATH` si el agente procesa prompts de terceros.

### API Key

La `OPENROUTER_API_KEY` se lee desde el entorno y **nunca debe commitearse** en el repositorio. Usar `.gitignore` para excluir archivos `.env`:

```gitignore
.env
.env.local
*.env
```

---

## Configuración de tests

Para tests que requieren API key real:

```bash
RUN_LIVE_TESTS=1 OPENROUTER_API_KEY=sk-or-... python -m pytest tests/ -m live
```

Sin `RUN_LIVE_TESTS=1`, los tests marcados con `@pytest.mark.live` se saltean automáticamente.
