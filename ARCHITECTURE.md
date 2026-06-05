# ARCHITECTURE.md

> Mapa de alto nivel del sistema. Punto de entrada para nuevos contribuidores.
> Fuente de verdad sobre capas, límites de dominio y decisiones técnicas.

---

## Visión general

Este proyecto es un agente de codificación: envuelve un LLM con un harness para que pueda razonar y actuar sobre herramientas reales.

```
Agent = Model + Harness
```

El modelo aporta el razonamiento. El harness aporta ejecución, control y seguridad operativa.

---

## Capas de la arquitectura

```
┌──────────────────────────────────────────────────────┐
│                    Entrypoint                        │
│                     app/main.py                      │
└──────────────────────┬───────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────┐
│                    Agent Loop                        │
│                    app/agent.py                      │
│     ReAct: Reason -> Act -> Observe -> Repeat        │
│     max_iterations=40 · max_tokens=4000              │
└─────────┬──────────────────────────┬─────────────────┘
          │                          │
┌─────────▼─────────┐      ┌─────────▼──────────────────┐
│   LLM Providers   │      │        Tool System          │
│  app/providers/   │      │   app/tool.py · app/tools.py│
│                   │      │                             │
│ base.py (ABC)     │      │ ToolRegistry                │
│   └─ LLMProvider  │      │ ├── read_file               │
│   └─ LLMResponse  │      │ ├── write_file              │
│   └─ ToolCallReq  │      │ └── bash_terminal           │
│                   │      │                             │
│ registry.py       │      │ PermissionPolicy            │
│   └─ ProviderSpec │      │ ├── AlwaysAsk               │
│                   │      │ ├── AlwaysAllow             │
│ openai_compat_    │      │ ├── AskOnce                 │
│   provider.py     │      │ └── AllowList               │
│ antropic_         │      └─────────────────────────────┘
│   provider.py     │
└───────────────────┘
```

---

## Estructura de directorios

```
.
├── ARCHITECTURE.md              ← este archivo
├── README.md
├── TODO.md
│
├── app/
│   ├── main.py                  ← CLI + factory de provider + factory de policy
│   ├── agent.py                 ← AgentLoop (provider-agnostic)
│   ├── tool.py                  ← Tool ABC + ToolRegistry + PermissionPolicy
│   ├── tools.py                 ← read/write/bash + create_default_registry
│   └── providers/
│       ├── base.py              ← LLMProvider ABC + dataclasses
│       ├── openai_compat_provider.py
│       ├── antropic_provider.py
│       └── registry.py          ← ProviderSpec + PROVIDERS
│
├── docs/
│   ├── agent-loop.md
│   ├── introduccion.md
│   ├── permisos.md
│   ├── providers.md
│   ├── tools-basicas.md
│   └── exec-plans/
│
└── tests/
    ├── conftest.py
    ├── test_agent.py
    ├── test_main.py
    ├── test_tool_registry.py
    └── ...
```

---

## Componentes clave

### AgentLoop (`app/agent.py`)

Implementa el ciclo ReAct y normaliza dos contratos de provider:

- `LLMProvider` moderno (async, `chat_with_retry`)
- cliente legacy estilo OpenAI (`chat.completions.create`)

Flujo simplificado:

```
run(prompt)
  -> messages = [{"role": "user", "content": prompt}]
  -> for iteration in range(max_iterations):
       response = _chat()
       normalize(response)
       if no tool_calls:
           return content
       _handle_tool_calls(tool_calls)
  -> raise RuntimeError("max_iterations reached")
```

Limitaciones actuales:

- No hay system prompt global
- No hay gestión avanzada de contexto por ventana de tokens
- No hay memoria persistente entre ejecuciones
- La API pública de `AgentLoop` es síncrona (puentea providers async internamente)

### Tool System (`app/tool.py`, `app/tools.py`)

`ToolRegistry.execute` pasa por una política de permisos antes de ejecutar:

```
agent loop -> permission policy -> registry.execute
```

Tools por defecto:

| Tool | Operación |
|------|-----------|
| `read_file` | Lee archivos |
| `write_file` | Escribe archivos |
| `bash_terminal` | Ejecuta shell |

Políticas incluidas:

| Política | Comportamiento |
|----------|----------------|
| `AlwaysAsk` | Pregunta cada vez |
| `AlwaysAllow` | Auto-ejecuta |
| `AskOnce` | Pregunta una vez por tool y recuerda |
| `AllowList{names}` | Auto-ejecuta tools listadas y pregunta el resto |

Advertencia: `bash_terminal` usa `shell=True` y no está sandboxed.

### Provider Layer (`app/providers/`)

Abstrae APIs LLM detrás de `LLMProvider`:

- `OpenAICompatProvider` para endpoints OpenAI-compatible
- `AnthropicProvider` para SDK nativo Anthropic
- `ProviderSpec` (`registry.py`) como metadata de selección y configuración

`main.py` resuelve provider con `find_by_name`, valida credenciales por `env_key`, y crea la implementación concreta según `spec.backend`.

---

## Flujo de datos

```
CLI: uv run -m app.main -p "prompt" --provider openrouter --permission-policy ask_once
      │
      ▼
main.py
  -> _build_llm_provider()
  -> _build_permission_policy()
  -> AgentLoop + ToolRegistry
      │
      ▼
AgentLoop.run(prompt)
      │
      ├─► _chat() -> provider call
      │
      ├─► [si tool_calls] ToolRegistry.execute(name, **args)
      │         ├─► PermissionPolicy.decide(name, args)
      │         ├─► read_file / write_file -> filesystem
      │         └─► bash_terminal -> subprocess (host)
      │
      └─► [si no tool_calls] return content
```

---

## Decisiones de diseño

| Decisión | Razón |
|----------|-------|
| OpenAI-compatible como protocolo base | Compatibilidad amplia con gateways y modelos |
| `AgentLoop` agnóstico al provider | Permite integrar `openai_compat` y `anthropic` sin cambiar el loop |
| `PermissionPolicy` desacoplada del loop | Control configurable de riesgo por sesión/CLI |
| Tool como ABC con schema OpenAI | Registro simple y sin configuración manual extra |
| `max_iterations=40` | Límite duro contra loops infinitos |

---

## Lo que este sistema NO es (todavia)

- No tiene sandbox de ejecucion de comandos
- No tiene memoria persistente entre sesiones
- No tiene planificacion estructurada dentro del loop
- No tiene observabilidad avanzada mas alla de logs y stderr

Ver [TODO.md](TODO.md) y [docs/exec-plans/PLAN.md](docs/exec-plans/PLAN.md) para roadmap.

---

## Referencias

- [Agent Loop](docs/agent-loop.md)
- [Providers](docs/providers.md)
- [Tools basicas](docs/tools-basicas.md)
- [Permisos](docs/permisos.md)
- [Plan de ejecucion](docs/exec-plans/PLAN.md)
- [TODO](TODO.md)
