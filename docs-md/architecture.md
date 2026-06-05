# Arquitectura

> Mapa de alto nivel del sistema. Punto de entrada para nuevos contribuidores.
> Fuente de verdad sobre capas, limites de dominio y decisiones tecnicas.

---

## Vision general

Este proyecto es un agente de codificacion: envuelve un LLM con un harness para que pueda razonar y actuar sobre herramientas reales.

```text
Agent = Model + Harness
```

El modelo aporta el razonamiento. El harness aporta ejecucion, control y seguridad operativa.

---

## Capas de la arquitectura

```text
┌──────────────────────────────────────────────────────┐
│                    Entrypoint                        │
│          app/main.py · app/server.py                │
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
│  app/providers/   │      │         app/tools/          │
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

```text
.
├── ARCHITECTURE.md              ← resumen raiz
├── README.md
├── TODO.md
│
├── app/
│   ├── main.py                  ← CLI entrypoint
│   ├── server.py                ← FastAPI entrypoint
│   ├── agent.py                 ← AgentLoop (provider-agnostic)
│   ├── tools/
│   │   ├── base.py              ← Tool ABC + ToolRegistry
│   │   ├── permission_policy.py ← AlwaysAsk/AlwaysAllow/AskOnce/AllowList
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   └── bash.py
│   └── providers/
│       ├── base.py              ← LLMProvider ABC + dataclasses
│       ├── openai_compat_provider.py
│       ├── antropic_provider.py
│       └── registry.py          ← ProviderSpec + PROVIDERS
│
├── docs-md/                     ← fuente markdown para MkDocs
│   ├── architecture.md          ← este archivo
│   ├── introduccion.md
│   ├── api.md
│   ├── agent-loop.md
│   ├── providers.md
│   ├── tools-basicas.md
│   ├── permisos.md
│   └── exec-plans/
│
├── docs/                        ← sitio HTML generado por MkDocs
│
└── tests/
```

---

## Componentes clave

### AgentLoop (app/agent.py)

Implementa el ciclo ReAct y normaliza dos contratos de provider:

- `LLMProvider` moderno (async, `chat_with_retry`)
- cliente legacy estilo OpenAI (`chat.completions.create`)

Flujo simplificado:

```text
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

### Tool System (app/tools/)

`ToolRegistry.execute` pasa por una politica de permisos antes de ejecutar:

```text
agent loop -> permission policy -> registry.execute
```

Tools por defecto:

| Tool | Operacion |
|---|---|
| `read_file` | Lee archivos |
| `write_file` | Escribe archivos |
| `bash_terminal` | Ejecuta shell |

### Provider Layer (app/providers/)

Abstrae APIs LLM detras de `LLMProvider`:

- `OpenAICompatProvider` para endpoints OpenAI-compatible
- `AnthropicProvider` para SDK nativo Anthropic
- `ProviderSpec` (`registry.py`) como metadata de seleccion y configuracion

`main.py` y `server.py` montan `AgentLoop` usando `build_llm_provider`, `build_permission_policy` y `build_tools`.

---

## Flujo de datos

```text
CLI: uv run -m app.main -p "prompt" --provider openrouter --permission-policy ask_once
API: POST /ask (app.server)
      │
      ▼
main.py / server.py
  -> build_llm_provider()
  -> build_permission_policy()
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

## Referencias

- [Introduccion](introduccion.md)
- [API HTTP](api.md)
- [Agent Loop](agent-loop.md)
- [Providers](providers.md)
- [Tools basicas](tools-basicas.md)
- [Permisos](permisos.md)
- [Plan de ejecucion](exec-plans/PLAN.md)
