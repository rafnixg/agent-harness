# Providers

La capa de proveedores abstrae la comunicación con APIs de LLM. Permite cambiar de modelo o proveedor sin tocar el código del agente.

---

## Jerarquía de clases

```
LLMProvider (ABC)          ← app/providers/base.py
└── OpenAICompatProvider   ← app/providers/openai_compat_provider.py
```

---

## `LLMProvider` — clase base abstracta

```
app/providers/base.py
```

Define la interfaz que todo proveedor debe implementar.

### Método abstracto obligatorio

```python
@abstractmethod
async def chat(
    self,
    messages: list[dict[str, Any]],
    model: str,
    tools: list[dict[str, Any]] | None = None,
    **kwargs,
) -> LLMResponse:
    ...
```

### Método concreto: `chat_with_retry`

Envuelve `chat()` con lógica de reintentos para errores transitorios:

```python
async def chat_with_retry(self, messages, model, tools=None, **kwargs) -> LLMResponse:
```

- Reintentos: hasta 3 veces con delays `[1, 2, 4]` segundos.
- Un error es "transitorio" si su representación en string contiene alguno de los marcadores en `_TRANSIENT_ERROR_MARKERS`.
- Si el error no es transitorio, lanza inmediatamente.
- Si se agotan los 3 reintentos, propaga el último error.

### Métodos estáticos de sanitización

| Método | Propósito |
|---|---|
| `_sanitize_empty_content(messages)` | Reemplaza contenido vacío por `"(empty)"` o `None` según el rol |
| `_sanitize_request_messages(messages)` | Elimina campos internos (`_meta`) antes de enviar al LLM |
| `_strip_image_content(messages)` | Elimina bloques de imagen para proveedores que no los soporten |
| `_is_transient_error(exc)` | Devuelve `True` si la excepción es un error transitorio recuperable |

---

## Dataclasses de respuesta

### `LLMResponse`

```python
@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCallRequest]   # default: []
    finish_reason: str                  # default: "stop"
    usage: dict[str, int]               # tokens consumidos
    reasoning_content: str | None       # DeepSeek-R1, Kimi
    thinking_blocks: list[dict] | None  # Anthropic extended thinking
```

Propiedad de conveniencia: `has_tool_calls → bool`.

### `ToolCallRequest`

```python
@dataclass
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any]
    provider_specific_fields: dict | None
    function_provider_specific_fields: dict | None
```

Método `to_openai_tool_call()` serializa al formato estándar de tool_call de OpenAI.

### `GenerationSettings`

```python
@dataclass(frozen=True)
class GenerationSettings:
    temperature: float = 0.7
    max_tokens: int = 4096
    reasoning_effort: str | None = None
```

Se almacena en `provider.generation` y aplica como defaults a todas las llamadas.

---

## `OpenAICompatProvider`

```
app/providers/openai_compat_provider.py
```

Implementación concreta para cualquier API compatible con el formato de OpenAI: OpenRouter, OpenAI directo, LM Studio, Together AI, etc.

### Constructor

```python
OpenAICompatProvider(
    api_key: str | None = None,
    api_base: str | None = None,
    default_model: str = "gpt-5-mini",
    extra_headers: dict[str, str] | None = None,
    spec: ProviderSpec | None = None,
)
```

Internamente crea un `AsyncOpenAI` client.

### Normalización de tool IDs

Los distintos proveedores tienen restricciones distintas sobre el formato de `tool_call_id`. El proveedor normaliza automáticamente:

- **IDs cortos válidos** (9 caracteres alfanuméricos): se usan tal cual.
- **IDs largos o con caracteres especiales**: se reemplazan por un hash SHA-1 truncado a 9 caracteres.
- **IDs generados internamente**: 9 caracteres aleatorios alfanuméricos (`_short_tool_id()`).

### Sanitización de mensajes

`_sanitize_messages(messages)` filtra cada mensaje para conservar solo las claves permitidas por la API:

```python
_ALLOWED_MSG_KEYS = {"role", "content", "tool_calls", "tool_call_id", "name", "reasoning_content"}
```

### Métodos async

| Método | Descripción |
|---|---|
| `async chat(messages, model, tools, **kwargs)` | Llamada estándar, retorna `LLMResponse` |
| `async chat_stream(messages, model, tools, **kwargs)` | Streaming de chunks, retorna `LLMResponse` al completar |

---

## `ProviderSpec` y registro

```
app/providers/registry.py
```

`ProviderSpec` es un dataclass que describe un proveedor:

```python
@dataclass(frozen=True)
class ProviderSpec:
    name: str
    base_url: str
    env_key: str          # nombre de la variable de entorno con la API key
    gateway: bool = False # True si es un gateway (OpenRouter, etc.)
```

El registro permite obtener un proveedor configurado por nombre sin pasar parámetros manualmente:

```python
from app.providers.registry import get_provider

provider = get_provider("openrouter")
```

---

## Usar un proveedor local (Ollama / LM Studio)

```bash
OPENROUTER_BASE_URL=http://localhost:11434/v1
OPENROUTER_API_KEY=ollama
OPENROUTER_MODEL=llama3
```

No se requiere ningún cambio en código. El `OpenAICompatProvider` funciona con cualquier endpoint que respete el formato de OpenAI.
