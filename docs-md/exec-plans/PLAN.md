# Plan de Ejecución — Harness Engineering

> Estado: **ACTIVO**
> Creado: 2026-06-03
> Basado en: OpenAI Harness Engineering, Martin Fowler, LangChain Anatomy, Anthropic Long-Running Agents

Este documento es un artefacto de primera clase. Registra decisiones, progreso y orden de implementación para convertir este agente básico en un harness robusto.

---

## Objetivo

Transformar el agente ReAct minimalista actual en un sistema con:
1. **Feedforward guides** — el agente recibe contexto estructurado antes de actuar
2. **Feedback sensors** — el sistema detecta y corrige errores automáticamente
3. **Memoria persistente** — el agente puede trabajar en sesiones largas sin perder contexto
4. **Seguridad** — ninguna herramienta puede comprometer el host

---

## Fases

### Fase 1 — Seguridad y Fundamentos (CRÍTICO)

**Prioridad: BLOQUEANTE**. El proyecto tiene vulnerabilidades activas que deben resolverse antes de continuar.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 1.1 | Sandboxear `bash_terminal` con allowlist de comandos | `app/tools.py` | Solo ejecuta comandos de la lista permitida; rechaza el resto |
| 1.2 | Añadir protección path traversal en `read_file` y `write_file` | `app/tools.py` | No puede leer/escribir fuera del workspace |
| 1.3 | Cambiar `shell=True` → `shell=False` con lista de argumentos | `app/tools.py` | Sin inyección de comandos vía shell |
| 1.4 | Validar que `WORKSPACE_PATH` existe antes de arrancar | `app/main.py` | Error claro si el workspace no existe |

**Razón:** `bash_terminal` con `shell=True` sin sandbox es OWASP A03 (Injection). Un prompt malicioso puede ejecutar cualquier comando en el host.

---

### Fase 2 — System Prompt y Context Feedforward

El agente actualmente opera sin instrucciones del sistema. Es el equivalente a contratar a un programador y no decirle nada sobre el proyecto.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 2.1 | Añadir parámetro `system_prompt` a `AgentLoop` | `app/agent.py` | El prompt del sistema se inyecta en `messages[0]` |
| 2.2 | Crear `AGENTS.md` como índice de contexto (~100 líneas) | `AGENTS.md` | El agente puede leerlo al inicio y navegar al contexto relevante |
| 2.3 | Cargar `AGENTS.md` automáticamente en el system prompt | `app/main.py` | Cada sesión empieza con el contexto del repositorio |
| 2.4 | Crear skill `how-to-use-tools` | `docs/skills/` | El agente sabe exactamente qué herramientas tiene y cómo usarlas |

**Inspiración:** OpenAI usa AGENTS.md como índice (~100 líneas), no como enciclopedia. La divulgación progresiva reduce el context rot.

---

### Fase 3 — Memoria y Estado Persistente

Sin memoria, cada sesión empieza desde cero. Para tareas largas, el agente no sabe qué se hizo antes.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 3.1 | Crear `ProgressTrackerTool` para leer/escribir `agent-progress.md` | `app/tools.py` | El agente puede registrar y leer su propio progreso |
| 3.2 | Añadir `GitTool` (status, log, commit, diff) | `app/tools.py` | El agente hace commits descriptivos al final de cada tarea |
| 3.3 | Añadir lógica de "get-up-to-speed" al inicio de sesión | `app/agent.py` | El agente lee git log + progress file antes de actuar |
| 3.4 | Crear `FeatureListTool` para leer/actualizar lista de tareas en JSON | `app/tools.py` | El agente no declara victoria prematuramente |

**Inspiración:** Anthropic recomienda `claude-progress.txt` + git log para que cada sesión nueva pueda retomar el trabajo. JSON es más estable que Markdown para que el agente no sobreescriba accidentalmente.

---

### Fase 4 — Feedback Sensors (Sensores Computacionales)

Los sensores de retroalimentación permiten que el agente detecte y corrija sus errores sin intervención humana.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 4.1 | Integrar `pytest` como tool en el loop | `app/tools.py` | El agente ejecuta tests y ve los resultados directamente |
| 4.2 | Integrar `ruff` como linter en el loop | `app/tools.py` | El agente puede verificar y corregir su propio código |
| 4.3 | Añadir `mypy`/`pyright` como sensor de tipos | `app/tools.py` | El agente detecta errores de tipos antes de declarar éxito |
| 4.4 | Crear hook post-ejecución que auto-corre linters | `app/agent.py` | Los errores de lint se añaden al contexto automáticamente |
| 4.5 | Mensaje de error de linter incluye instrucciones de remediación | `pyproject.toml` | Mensajes de error redactados para consumo del agente |

**Inspiración:** Martin Fowler — los sensores computacionales son baratos, deterministas y deben correr en cada cambio. Los mensajes de error deben incluir instrucciones de corrección (prompt injection positivo).

---

### Fase 5 — Context Management (Anti-Context Rot)

Sin gestión del contexto, el agente degrada su rendimiento al llenarse la ventana de contexto.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 5.1 | Añadir truncación de outputs de tools > N tokens | `app/agent.py` | Los outputs largos se truncan y se guarda el full en disco |
| 5.2 | Implementar compaction básica cuando se acerca el límite | `app/agent.py` | El agente puede continuar trabajando más allá de 1 context window |
| 5.3 | Agregar contador de tokens al ciclo del agente | `app/agent.py` | Visible en logs cuántos tokens se usan por sesión |
| 5.4 | Implementar Skills (progressive disclosure de tools) | `app/tool.py` | No todas las tools se cargan en contexto desde el inicio |

**Inspiración:** LangChain — "context rot" describe cómo el rendimiento degrada al llenarse la ventana. Tool call offloading y compaction son primitivos del harness.

---

### Fase 6 — Arquitectura y Enforcements

Sin enforcement arquitectónico, el agente (o un humano) puede violar las capas del sistema.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 6.1 | Arreglar desconexión: `main.py` debe usar `LLMProvider` en vez de `OpenAI` raw | `app/main.py` | No hay referencias directas al cliente `openai` fuera de providers/ |
| 6.2 | Añadir tests estructurales de dependencias (ArchUnit-style) | `tests/test_architecture.py` | CI falla si agent.py importa desde openai directamente |
| 6.3 | Configurar `ruff` con reglas de import/boundary | `pyproject.toml` | Las violaciones de capas se detectan en lint |
| 6.4 | Async: alinear agent.py para usar `await provider.chat()` | `app/agent.py` | Sin mezcla sync/async |

---

### Fase 7 — Observabilidad

El agente actualmente sólo imprime en stderr. No hay forma de inspeccionar sesiones pasadas.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 7.1 | Reemplazar prints con `loguru` estructurado | `app/agent.py` | Logs en JSON con campos consistentes |
| 7.2 | Añadir tracing de tool calls (input, output, duración) | `app/agent.py` | Cada tool call tiene un trace con timing |
| 7.3 | Añadir métricas de tokens por sesión | `app/agent.py` | Visible el costo de cada sesión |
| 7.4 | Crear `session_log.jsonl` por sesión | `app/agent.py` | Reproducible auditar cualquier sesión pasada |

---

### Fase 8 — Multi-Agente y Long-Horizon

Para tareas complejas que no caben en una sola sesión.

| # | Tarea | Archivo | Criterio de éxito |
|---|-------|---------|-------------------|
| 8.1 | Separar `InitializerAgent` de `CodingAgent` | `app/agent.py` | La primera sesión configura el entorno; las siguientes hacen progreso incremental |
| 8.2 | Implementar Ralph Loop (reinyectar prompt al agotar contexto) | `app/agent.py` | El agente no se detiene cuando se llena el contexto |
| 8.3 | Añadir spawning de subagentes | `app/tools.py` | El agente puede delegar subtareas a agentes especializados |

---

## Decisiones registradas

| Fecha | Decisión | Razón |
|-------|----------|-------|
| 2026-06-03 | Fase 1 (seguridad) es BLOQUEANTE para todo lo demás | `bash_terminal` sin sandbox es un riesgo inaceptable en producción |
| 2026-06-03 | AGENTS.md como índice, no enciclopedia | Contexto escaso; demasiada orientación = desorientación (OpenAI) |
| 2026-06-03 | JSON para feature list en vez de Markdown | El agente es menos propenso a sobreescribir JSON accidentalmente (Anthropic) |
| 2026-06-03 | Sensores computacionales antes que inferencial | Más baratos, deterministas, dan más valor por token (Fowler) |

---

## Deuda técnica conocida

Ver [TODO.md](../TODO.md) para la lista completa. Ítems críticos:

- [ ] `bash_terminal` sin sandbox — OWASP A03
- [ ] Path traversal en read/write file — OWASP A01
- [ ] `main.py` bypasea la capa de providers
- [ ] Sin system prompt → el agente no tiene instrucciones
- [ ] Sin memoria → cada sesión empieza desde cero

---

## Links

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [TODO.md](../TODO.md)
- [Agent Loop](../docs/agent-loop.md)
