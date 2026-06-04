# ARCHITECTURE.md

> Mapa de alto nivel del sistema. Punto de entrada para agentes y nuevos contribuidores.
> Fuente de verdad sobre la estructura de capas, límites de dominio y decisiones técnicas clave.

---

## Visión general

Este proyecto es un **agente de codificación** — un sistema que envuelve un modelo LLM con un *harness*:
todo el código, configuración y lógica de ejecución que no es el modelo en sí.

```
Agent = Model + Harness
```

El modelo contiene la inteligencia. El harness la hace útil.

---

## Capas de la arquitectura

```
┌─────────────────────────────────────────────────────┐
│                    Entrypoint                       │
│              app/main.py  ·  your_program.sh        │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                  Agent Loop                         │
│                  app/agent.py                       │
│   Patrón ReAct: Reason → Act → Observe → Repeat     │
│   max_iterations=40 · max_tokens=4000               │
└────────┬──────────────────────────┬─────────────────┘
         │                          │
┌────────▼────────┐      ┌──────────▼──────────────────┐
│  LLM Providers  │      │       Tool System            │
│ app/providers/  │      │  app/tool.py · app/tools.py  │
│                 │      │                              │
│ base.py (ABC)   │      │  ToolRegistry                │
│   └─ LLMProvider│      │  ├── read_file               │
│   └─ LLMResponse│      │  ├── write_file              │
│   └─ ToolCallReq│      │  └── bash_terminal           │
│                 │      │                              │
│ openai_compat_  │      │  Tool (ABC)                  │
│   provider.py   │      │  name · description          │
│ antropic_       │      │  parameters · execute()      │
│   provider.py   │      └──────────────────────────────┘
│ registry.py     │
└─────────────────┘
```

---

## Estructura de directorios

```
.
├── AGENTS.md                    ← [ FALTA ] índice para el agente
├── ARCHITECTURE.md              ← este archivo
├── TODO.md                      ← trabajo pendiente
│
├── app/
│   ├── main.py                  ← entrypoint CLI (-p "prompt")
│   ├── agent.py                 ← AgentLoop (ReAct)
│   ├── tool.py                  ← Tool ABC + ToolRegistry
│   ├── tools.py                 ← implementaciones concretas
│   └── providers/
│       ├── base.py              ← LLMProvider ABC + dataclasses
│       ├── openai_compat_provider.py
│       ├── antropic_provider.py
│       └── registry.py          ← ProviderSpec + PROVIDERS list
│
├── docs/
│   ├── agent-loop.md
│   ├── introduccion.md
│   ├── permisos.md
│   ├── providers.md
│   ├── tools-basicas.md
│   └── exec-plans/              ← [ FALTA ] planes de ejecución activos
│
└── tests/
    ├── conftest.py
    ├── test_agent.py
    ├── test_tools.py
    ├── test_providers_base.py
    └── ...
```

---

## Componentes clave

### AgentLoop (`app/agent.py`)

Núcleo del sistema. Implementa el ciclo ReAct:

```
run(prompt)
  → messages = [{"role": "user", "content": prompt}]
  → for iteration in range(max_iterations):
      response = _chat()               # LLM call
      if not response.tool_calls:
          return response.content      # DONE
      _handle_tool_calls(tool_calls)   # execute + append results
  → raise RuntimeError("max_iterations reached")
```

**Limitaciones actuales (ver TODO.md):**
- No tiene system prompt
- Sin gestión de contexto (context window overflow no manejado)
- Sin memoria persistente entre sesiones
- Síncrono aunque los providers son async

### Tool System (`app/tool.py`, `app/tools.py`)

Interfaz uniforme para las acciones del agente. Expone schema OpenAI.

| Tool | Operación |
|------|-----------|
| `read_file` | Lee archivos del filesystem |
| `write_file` | Escribe archivos |
| `bash_terminal` | Ejecuta comandos de shell |

**Advertencia de seguridad:** `bash_terminal` ejecuta comandos directamente en el host sin sandbox. Ver TODO.md.

### Provider Layer (`app/providers/`)

Abstrae la comunicación con APIs de LLM detrás de una interfaz unificada.

- `LLMProvider` (ABC): `chat()`, `chat_with_retry()`, sanitización de mensajes
- `OpenAICompatProvider`: cualquier API compatible con OpenAI (OpenRouter, Mistral, etc.)
- `AnthropicProvider`: SDK nativo de Anthropic (prompt caching, extended thinking)
- `ProviderRegistry`: metadata de providers, detección automática por key/base URL

**Desconexión actual:** `main.py` instancia `OpenAI` directamente en lugar de usar `LLMProvider`.

---

## Flujo de datos

```
CLI: uv run -m app.main -p "prompt"
      │
      ▼
main.py → crea OpenAI client + AgentLoop + registra tools → agent.run(prompt)
      │
      ▼
AgentLoop.run(prompt)
      │
      ├─► _chat() → OpenAI API (vía OpenRouter) → LLMResponse
      │
      ├─► [si tool_calls] → ToolRegistry.execute(name, **args)
      │         ├─► read_file    → filesystem
      │         ├─► write_file   → filesystem
      │         └─► bash_terminal → subprocess (host)
      │
      └─► [si no tool_calls] → return content
```

---

## Decisiones de diseño

| Decisión | Razón |
|----------|-------|
| OpenAI-compatible como protocolo estándar | Máxima compatibilidad con OpenRouter y providers alternativos |
| Tool como ABC con schema OpenAI embebido | Registro automático sin configuración manual del schema |
| `max_iterations=40` como límite duro | Previene bucles infinitos; configurable por instancia |
| Documentación en `docs/` en español | Proyecto de aprendizaje en español |

---

## Lo que este sistema NO es (todavía)

- No tiene **sandbox** para ejecución segura de código
- No tiene **memoria persistente** entre sesiones
- No tiene **planificación estructurada** (feature list, progress file)
- No tiene **sensores de retroalimentación** (linters, tests en el loop)
- No tiene **orquestación multi-agente**
- No tiene **observabilidad** más allá de prints en stderr

Ver [TODO.md](./TODO.md) y [docs/exec-plans/PLAN.md](./docs/exec-plans/PLAN.md) para el roadmap completo.

---

## Referencias

- [Agent Loop](docs/agent-loop.md)
- [Providers](docs/providers.md)
- [Tools básicas](docs/tools-basicas.md)
- [Plan de ejecución](docs/exec-plans/PLAN.md)
- [TODO](TODO.md)
