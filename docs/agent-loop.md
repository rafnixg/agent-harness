# Agent Loop

El **Agent Loop** es el núcleo del sistema. Implementa el patrón _ReAct_ (Reason + Act): el agente razona con el LLM, actúa ejecutando herramientas, observa el resultado y repite hasta obtener una respuesta final.

---

## Clase `AgentLoop`

```
app/agent.py → class AgentLoop
```

### Constructor

```python
AgentLoop(
    llm_provider: Any,           # provider LLM (openai_compat, anthropic, etc.)
    workspace: Path,             # directorio de trabajo
    model: str | None = None,    # modelo a usar (default: proveedor decide)
    max_iterations: int = 40,    # límite de ciclos por ejecución
    max_tokens: int = 4000,      # tokens máximos por respuesta del LLM
)
```

El `ToolRegistry` se crea vacío en `__init__`. Las herramientas se registran en `agent.tools` antes de llamar a `run()`.

---

## Flujo de ejecución

```
run(prompt)
│
├─ messages = [{"role": "user", "content": prompt}]
│
└─ for _iteration in range(max_iterations):
       │
    ├─ response = _chat()          ← llamada al LLM (provider-agnostic)
       │
    ├─ normaliza respuesta (OpenAI client o LLMResponse)
    ├─ messages.append(assistant_message)
    │
    ├─ if no hay tool_calls:
    │      return content          ← RESPUESTA FINAL
    │
    └─ _handle_tool_calls(tool_calls)
        │
        ├─ parse tool name + arguments (JSON)
        ├─ permission_policy.decide(name, args)
        ├─ tools.execute(name, **args)
        └─ messages.append({"role": "tool", "content": result, ...})

raise RuntimeError("max_iterations reached: 40")
```

### Estados posibles al final de un ciclo

| Estado | Condición | Siguiente paso |
|---|---|---|
| **Respuesta final** | `message.tool_calls` es vacío | Retorna `message.content` |
| **Tool call** | `message.tool_calls` contiene funciones | Ejecuta herramientas y continúa |
| **Sin choices** | `response.choices` está vacío | `RuntimeError` inmediato |
| **Límite alcanzado** | `_iteration == max_iterations - 1` | `RuntimeError` |

---

## `_chat()` — llamada al LLM

```python
def _chat(self):
    if provider implementa LLMProvider:
        return chat_with_retry(...)
    return openai_client.chat.completions.create(...)
```

El agente soporta ambos contratos:

- providers basados en `LLMProvider` (`chat_with_retry`)
- clientes estilo OpenAI (`chat.completions.create`)

---

## `_handle_tool_calls()` — ejecución de herramientas

Para cada `tool_call` en la respuesta:

1. Verifica que `type == "function"` (ignora tipos desconocidos con log a stderr).
2. Deserializa `function.arguments` (JSON).
3. Llama a la política de permisos y luego a `tools.execute(name, **args)`.
4. Captura `KeyError`, `FileNotFoundError`, `ValueError`, `OSError` y los convierte en strings de error (el agente puede recuperarse sin abortar).
5. Agrega un mensaje `role: tool` al historial con el resultado.

---

## Protección contra bucles infinitos

La versión original usaba `while True:` ignorando `max_iterations`. El bug fue corregido: el loop ahora usa `for _iteration in range(self.max_iterations)` y lanza `RuntimeError` al agotar las iteraciones.

```python
for _iteration in range(self.max_iterations):
    ...

raise RuntimeError(f"max_iterations reached: {self.max_iterations}")
```

---

## Historial de mensajes

El historial se reinicia completamente en cada llamada a `run()`:

```python
self.messages = [{"role": "user", "content": prompt}]
```

Esto significa que **cada invocación es stateless** — el agente no recuerda conversaciones anteriores entre llamadas a `run()`. Si se necesita memoria entre sesiones, debe pasarse como parte del prompt.

---

## Diagrama de secuencia

```mermaid
sequenceDiagram
    actor User
    participant Agent as AgentLoop
    participant LLM
    participant Policy as PermissionPolicy
    participant Tool as ToolRegistry

    User->>Agent: run("crea un archivo data.txt")
    Agent->>LLM: chat(messages, tools)
    LLM-->>Agent: tool_call: write_file(...)
    Agent->>Policy: decide("write_file", args)
    Policy-->>Agent: allow/ask/deny
    Agent->>Tool: execute("write_file", ...)
    Tool-->>Agent: "Successfully wrote to data.txt"
    Agent->>LLM: chat(messages + tool result)
    LLM-->>Agent: "El archivo data.txt fue creado."
    Agent-->>User: "El archivo data.txt fue creado."
```
