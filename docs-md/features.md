# features.md

> Inventario de capacidades del harness.
> Objetivo: saber rapidamente que ya existe y que falta.

Estado:
- `Implemented`: funcionalidad disponible en el codigo actual.
- `Partial`: existe una base, pero faltan piezas importantes.
- `Missing`: no existe aun.

Fuentes de referencia:
- `ARCHITECTURE.md`
- `TODO.md`
- `app/`, `tests/`

---

## 1) Runtime interfaces

| Feature | Status | Notes |
|---|---|---|
| CLI para ejecutar prompt (`app.main`) | Implemented | Soporta `-p`, `--provider`, `--model`, `--workspace`, politicas de permiso |
| API HTTP (`app.server`) | Implemented | `GET /health`, `POST /ask` |
| Servidor con `uvicorn` via modulo | Implemented | `uv run -m app.server --host --port --reload` |
| Modo streaming de respuesta al cliente | Missing | `POST /ask` devuelve respuesta final completa |

---

## 2) Agent loop

| Feature | Status | Notes |
|---|---|---|
| Loop ReAct (reason -> act -> observe) | Implemented | `AgentLoop.run()` |
| Max iterations guard | Implemented | Default `max_iterations=40` |
| Max tokens por llamada | Implemented | Default `max_tokens=4000` |
| Soporte provider moderno (`LLMProvider`) | Implemented | Usa `chat_with_retry` |
| Soporte cliente estilo OpenAI legacy | Implemented | Rama `chat.completions.create` |
| Manejo de errores de tools en loop | Implemented | Captura `KeyError/FileNotFoundError/ValueError/OSError` |
| System prompt global configurable | Missing | No parametro `system_prompt` en `AgentLoop` |
| Memoria persistente entre runs | Missing | `messages` se reinicia en cada `run()` |
| Compaction/truncacion de contexto | Missing | No estrategia anti-context-rot |

---

## 3) Providers

| Feature | Status | Notes |
|---|---|---|
| Registro de providers por metadata (`ProviderSpec`) | Implemented | `app/providers/registry.py` |
| Factory de providers (`build_llm_provider`) | Implemented | Seleccion por `spec.backend` |
| OpenAI-compatible provider | Implemented | `OpenAICompatProvider` |
| Anthropic provider | Implemented | `AnthropicProvider` |
| Retry en errores transitorios | Implemented | `LLMProvider.chat_with_retry` |
| Seleccion de provider por env/CLI | Implemented | `LLM_PROVIDER`, `--provider` |
| Telemetria/metricas de tokens visibles por sesion | Partial | existe `_last_usage` pero no reporte final robusto |

---

## 4) Tooling

| Feature | Status | Notes |
|---|---|---|
| Tool ABC + ToolRegistry | Implemented | `app/tools/base.py` |
| Tool `read_file` | Implemented | Lectura de archivo |
| Tool `write_file` | Implemented | Escritura de archivo |
| Tool `bash_terminal` | Implemented | Ejecuta comandos shell |
| Politicas de permisos (`always_ask`, `always_allow`, `ask_once`, `allow_list`) | Implemented | `app/tools/permission_policy.py` |
| Factory de herramientas (`build_tools`) | Implemented | registra tools por defecto |
| Sandboxing de comandos para `bash_terminal` | Missing | No aislamiento fuerte |
| Timeout para comandos shell | Missing | Riesgo de bloqueo por comando largo |
| Restriccion de lectura/escritura al workspace | Missing | Falta validacion anti path traversal |
| Limite de tamano de lectura de archivos | Missing | Falta `max_bytes` configurable |

---

## 5) Seguridad

| Feature | Status | Notes |
|---|---|---|
| Politicas de permiso por tool call | Implemented | primer control de riesgo |
| Confirmacion interactiva por tool call | Implemented | en `AlwaysAsk` y `AskOnce` |
| Sandbox de ejecucion de tools | Missing | no hay aislamiento de proceso/sistema |
| Validacion estricta de rutas de archivo | Missing | pendiente en `read_file`/`write_file` |
| Hardening de comandos (`shell=False`, allowlist) | Missing | pendiente en `bash_terminal` |

---

## 6) Calidad y testing

| Feature | Status | Notes |
|---|---|---|
| Suite de tests unitarios/integracion | Implemented | `tests/` |
| Tests de API FastAPI | Implemented | `tests/test_server.py` |
| Build de docs con MkDocs | Implemented | `mkdocs.yml`, `docs-md` |
| GitHub Action de docs | Implemented | `.github/workflows/docs.yml` |
| CI de calidad completa (lint + tests + typecheck) | Missing | pendiente workflow `ci.yml` |
| Coverage minimo enforced | Missing | no `--cov-fail-under` obligatorio |
| Hooks pre-commit | Missing | no `.pre-commit-config.yaml` |

---

## 7) Observabilidad

| Feature | Status | Notes |
|---|---|---|
| Logs basicos de tool calls | Partial | `print(..., stderr)` |
| Logging estructurado JSON | Missing | no tracing estructurado |
| Session log persistente (`jsonl`) | Missing | no auditoria completa por sesion |
| Metricas de duracion por tool | Missing | no instrumentation de tiempos |

---

## 8) Conocimiento y guidance para el agente

| Feature | Status | Notes |
|---|---|---|
| Documentacion funcional (`docs-md`) | Implemented | intro, arquitectura, api, providers, tools, permisos |
| Roadmap y gaps tecnicos (`TODO.md`) | Implemented | backlog priorizado |
| Archivo guia `AGENTS.md` | Missing | recomendado para feedforward |
| Skills docs accionables para tareas repetidas | Missing | sugerido `docs/skills/` |
| Referencias de librerias para el agente | Missing | sugerido `docs/references/` |

---

## 9) Slash commands

| Feature | Status | Notes |
|---|---|---|
| Router de slash commands en CLI/TUI | Missing | No parser dedicado para comandos tipo `/algo` |
| `/resume` (resumen de sesion actual) | Missing | Debe condensar objetivo, cambios y siguientes pasos |
| Slash command para estado (`/status` o equivalente) | Missing | Mostrar tests, docs y archivos tocados |
| Slash command para ayuda (`/help`) | Missing | Descubrimiento de comandos disponibles |
| Registro de comandos ejecutados por sesion | Missing | Base para auditoria y UX |

### Especificacion minima sugerida para `/resume`

Input esperado:
- opcional: nivel de detalle (`short`, `medium`, `full`)

Output esperado:
1. Objetivo actual de la sesion
2. Cambios completados (archivos y resultado)
3. Riesgos pendientes
4. Siguientes pasos recomendados

Ejemplo de salida esperada:

```text
Resumen (short)
- Objetivo: exponer API del agente y mejorar docs.
- Completado: endpoint /ask, docs MkDocs, tests en verde.
- Pendiente: hardening de seguridad en tools.
- Siguiente paso: agregar guards de path traversal + timeout de bash.
```

---

## 10) TUI (Terminal UI)

| Feature | Status | Notes |
|---|---|---|
| TUI interactiva para chat con el agente | Missing | Hoy la UX principal es CLI por flags |
| Panel de contexto (provider/model/workspace/permisos) | Missing | Debe ser visible y editable en vivo |
| Stream de eventos del loop (thought/tool/result) | Missing | Mejora trazabilidad durante ejecucion |
| Acciones rapidas (run tests, build docs, open logs) | Missing | Atajos para feedback rapido |
| Integracion de slash commands en TUI | Missing | `/resume`, `/help`, `/status`, etc. |

---

## 11) Extensibilidad avanzada (MCP, Skills, Subagents, Memoria)

| Feature | Status | Notes |
|---|---|---|
| Soporte MCP (Model Context Protocol) | Missing | No cliente/registry MCP integrado en runtime |
| Descubrimiento de herramientas MCP dinamicas | Missing | Sin handshake/capabilities negotiation |
| Skills cargables por demanda | Missing | No progressive disclosure de tools/contexto |
| Catalogo de Skills con metadata | Missing | Falta indice con trigger, scope y dependencias |
| Soporte de subagents | Missing | No delegacion de subtareas a loops secundarios |
| Estrategia de coordinacion entre subagents | Missing | Sin planner/scheduler ni merge de resultados |
| Memoria persistente de sesion | Missing | No persistencia durable de estado operativo |
| Memoria de largo plazo (cross-session) | Missing | Sin store para decisiones/artefactos historicos |

---

## 12) Alineacion con Harness Engineering

Referencias solicitadas:
- OpenAI Harness Engineering: `https://openai.com/es-ES/index/harness-engineering/`
- Martin Fowler Harness Engineering: `https://martinfowler.com/articles/harness-engineering.html`

Aplicacion al roadmap de este repo:
1. Feedforward: `AGENTS.md` + system prompt + skills operativas.
2. Feedback loops: sensores de calidad dentro del loop (`pytest`, `ruff`, typecheck).
3. Reliability: memoria persistente + resume/status + observabilidad estructurada.
4. Safety: sandboxing de tools + boundaries por workspace + politicas verificables.

---

## 13) Resumen ejecutivo

- El harness ya cubre el nucleo: `CLI + API + loop + providers + tools + permisos + tests`.
- Los gaps mas importantes estan en `seguridad`, `observabilidad`, `self-verification` y `orquestacion avanzada`.
- Prioridad recomendada inmediata:
  1. Path traversal guards en `read_file`/`write_file`.
  2. Timeout + hardening en `bash_terminal`.
  3. Integrar sensores automaticos (`pytest`, `ruff`, typecheck) dentro del loop o como paso obligatorio de cierre.
  4. Implementar `/resume` + base de memoria de sesion.
  5. Definir arquitectura base para MCP/Skills/Subagents.

---

## 14) Checklist rapido de release

Antes de considerar el harness listo para uso mas amplio:

- [ ] Seguridad minima de tools implementada
- [ ] CI completa (lint + test + typecheck)
- [ ] Logging estructurado + session logs
- [ ] AGENTS.md y guias de skills
- [ ] Politica de verificacion automatica antes de declarar exito
- [ ] Slash commands minimos (`/help`, `/status`, `/resume`)
- [ ] MVP de memoria persistente de sesion
- [ ] Plan de integracion MCP y subagents
