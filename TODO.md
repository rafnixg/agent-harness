# TODO — Harness Engineering Gaps

> Análisis basado en: OpenAI Harness Engineering, Martin Fowler, LangChain Anatomy of an Agent Harness, Anthropic Effective Harnesses for Long-Running Agents.
>
> Formato: `[ ]` pendiente · `[~]` en progreso · `[x]` completado
> Prioridades: 🔴 CRÍTICO · 🟠 ALTA · 🟡 MEDIA · 🟢 BAJA

---

## 🔴 SEGURIDAD (BLOQUEANTE)

Vulnerabilidades activas. Deben resolverse antes de cualquier otra mejora.

- [ ] **`bash_terminal` sin sandbox** — ejecuta `shell=True` directamente en el host. Un prompt malicioso puede ejecutar `rm -rf /`, exfiltrar credenciales o comprometer el sistema. OWASP A03 (Injection). **Fix:** allowlist de comandos + `shell=False` + ejecución en directorio aislado.

- [ ] **Path traversal en `read_file`** — `ReadFileTool.execute()` no valida que `file_path` esté dentro del workspace. El agente puede leer `/etc/passwd` o cualquier archivo del sistema. OWASP A01 (Broken Access Control). **Fix:** `Path(file_path).resolve()` y verificar que empiece con `workspace`.

- [ ] **Path traversal en `write_file`** — `WriteFileTool.execute()` tiene el mismo problema. El agente puede sobrescribir cualquier archivo del sistema. **Fix:** misma validación que read_file.

- [ ] **Sin límite de tamaño en `read_file`** — un archivo de 1GB llena la memoria y el contexto del agente. **Fix:** añadir `max_bytes` configurable.

- [ ] **Sin límite de tiempo en `bash_terminal`** — un comando que no termina bloquea el agente indefinidamente. **Fix:** `timeout` en `subprocess.run()`.

---

## 🟠 HARNESS — FEEDFORWARD (Guías de entrada)

El agente actúa sin instrucciones del sistema. Es como contratar un programador sin decirle nada sobre el proyecto.

- [ ] **Sin system prompt** — `AgentLoop` no tiene soporte para `system_prompt`. El agente no tiene instrucciones sobre cómo trabajar, qué herramientas usar ni cómo comportarse. **Fix:** añadir `system_prompt: str | None` a `AgentLoop.__init__()`.

- [ ] **Sin `AGENTS.md`** — no existe el archivo índice que orienta al agente sobre el repositorio. OpenAI y LangChain coinciden en que es el primer artefacto del harness. **Fix:** crear `AGENTS.md` como índice (~100 líneas) apuntando a `ARCHITECTURE.md`, `docs/`, `TODO.md`.

- [ ] **Sin carga automática de contexto** — el agente no lee `AGENTS.md` al iniciar. El contexto del repositorio no llega al agente. **Fix:** `main.py` debe inyectar `AGENTS.md` en el system prompt.

- [ ] **Sin skills / how-to docs** — no hay guías de "cómo hacer X" para el agente (cómo ejecutar tests, cómo hacer commits, cómo estructurar código). **Fix:** crear `docs/skills/` con archivos Markdown por tarea.

- [ ] **Sin documentación de referencia para el agente** — el agente no tiene acceso a docs de las librerías que usa (loguru, openai, anthropic). **Fix:** añadir `docs/references/` con `llms.txt` de las dependencias clave.

---

## 🟠 HARNESS — FEEDBACK SENSORS (Sensores de retroalimentación)

Sin sensores, el agente no puede corregir sus errores. Declara éxito antes de verificar.

- [ ] **Sin integración de `pytest` en el loop** — el agente no puede ejecutar los tests del proyecto para verificar su trabajo. Anthropic encontró que sin esto, el agente marca features como completas sin verificar. **Fix:** `TestRunnerTool` que ejecute pytest y devuelva resultados estructurados.

- [ ] **Sin `ruff` en el loop** — el agente puede generar código con errores de estilo o bugs simples sin saberlo. Martin Fowler: los linters son los sensores computacionales más baratos. **Fix:** `LintTool` que ejecute `ruff check` y devuelva los errores con instrucciones de corrección.

- [ ] **Sin verificación de tipos en el loop** — el agente genera código sin verificar que los tipos sean correctos. **Fix:** `TypeCheckTool` para `mypy`/`pyright`.

- [ ] **Sin self-verification loop** — el agente no está instruido para auto-verificar su trabajo antes de declarar éxito. Anthropic: la tendencia a marcar features como completas sin testear es uno de los failure modes más comunes. **Fix:** instrucciones en system prompt + tool de verificación.

- [ ] **Sin sensor de cobertura** — el agente puede escribir tests que pasan pero no cubren el código nuevo. **Fix:** `CoverageTool` que ejecute `pytest --cov`.

---

## 🟠 MEMORIA Y ESTADO PERSISTENTE

Sin memoria, el agente empieza desde cero en cada sesión. Anthropic: "es como contratar ingenieros que trabajan en turnos donde cada uno llega sin memoria del turno anterior".

- [ ] **Sin progress file** — no existe un archivo donde el agente registre qué hizo, qué dejó pendiente y en qué estado está el código. **Fix:** crear `agent-progress.md` y `ProgressTrackerTool`.

- [ ] **Sin git integration** — el agente no puede hacer commits, leer el git log ni revertir cambios. Anthropic + LangChain: git es una primitiva fundamental del harness. **Fix:** `GitTool` con `status`, `log`, `commit`, `diff`, `checkout`.

- [ ] **Sin feature list** — no hay un archivo estructurado con las tareas pendientes. El agente puede declarar victoria prematuramente o intentar hacer todo de una vez. Anthropic recomienda JSON por ser más estable que Markdown. **Fix:** `feature_list.json` + `FeatureListTool`.

- [ ] **Sin `init.sh`** — no hay script para arrancar el entorno de desarrollo. El agente pierde tokens averiguando cómo ejecutar el proyecto cada sesión. **Fix:** crear `init.sh` con los comandos para arrancar, testear y verificar.

- [ ] **Sin memoria entre sesiones** — cada instancia de `AgentLoop` empieza vacía. No hay carga del historial de conversaciones anteriores. **Fix:** serialización/deserialización de `messages` a disco + lectura en `run()`.

---

## 🟠 CONTEXT MANAGEMENT (Anti-Context Rot)

LangChain: "context rot" describe cómo el rendimiento del agente degrada al llenarse la ventana de contexto.

- [ ] **Sin truncación de outputs de tools** — un `bash_terminal` que imprime 10,000 líneas inunda el contexto. **Fix:** truncar outputs > N tokens y guardar el full en disco con un path que el agente puede leer.

- [ ] **Sin compaction** — cuando la conversación se acerca al límite del contexto, el agente simplemente falla con un error de la API. **Fix:** implementar compaction (resumir el historial) antes de alcanzar el límite.

- [ ] **Sin contador de tokens visible** — no se puede saber cuántos tokens consume cada sesión ni cuando se está cerca del límite. **Fix:** añadir tracking de `usage` en cada llamada al LLM.

- [ ] **Sin progressive disclosure de tools** — todas las tools se cargan en contexto desde el inicio, degradando el rendimiento antes de que el agente empiece. **Fix:** implementar Skills (tools que se cargan bajo demanda).

---

## 🟠 ARQUITECTURA — ENFORCEMENT

Sin enforcement, las capas se violan sin que nadie lo note.

- [ ] **`main.py` bypasea la capa de providers** — `main.py` instancia `OpenAI` directamente en vez de usar `LLMProvider`. Viola la capa de abstracción. **Fix:** `main.py` debe crear un `OpenAICompatProvider` o `AnthropicProvider`.

- [ ] **`AgentLoop` es síncrono, providers son async** — `AgentLoop._chat()` llama `self.llm_provider.chat.completions.create()` de forma síncrona, pero los providers tienen interfaz `async`. Son dos sistemas incompatibles en el mismo proyecto. **Fix:** `AgentLoop.run()` debe ser `async` + `await`.

- [ ] **Sin tests estructurales de capas** — no hay tests que verifiquen que `agent.py` no importa directamente de `openai`. **Fix:** `tests/test_architecture.py` con checks de imports.

- [ ] **Sin linter de boundaries de módulos** — `ruff` no está configurado para detectar imports que violan capas. **Fix:** añadir reglas a `pyproject.toml`.

- [ ] **`tools.py` y `tool.py`** — naming confuso: `tool.py` tiene las ABCs, `tools.py` tiene las implementaciones. El agente (y los humanos) pueden confundirse. **Fix:** renombrar a `tool_base.py` / `tool_implementations.py` o documentar la diferencia en `ARCHITECTURE.md`.

---

## 🟡 OBSERVABILIDAD

El agente actualmente sólo imprime en stderr sin estructura. Es imposible auditar sesiones pasadas.

- [ ] **Logs no estructurados** — `print(f"Tool call: ...", file=sys.stderr)` no es parseable ni consultable. **Fix:** reemplazar con `loguru` en formato JSON.

- [ ] **Sin tracing de tool calls** — no hay registro de duración, inputs y outputs de cada tool call. **Fix:** decorar `ToolRegistry.execute()` con tracing.

- [ ] **Sin session log** — no existe un `session_log.jsonl` que permita reproducir o auditar sesiones. **Fix:** serializar el historial completo de `messages` al final de cada sesión.

- [ ] **Sin métricas de tokens** — `_last_usage` existe en `AgentLoop` pero nunca se usa. **Fix:** loggear el usage total al final de `run()`.

---

## 🟡 KNOWLEDGE BASE

OpenAI: "cualquier cosa que el agente no puede acceder en contexto mientras se ejecuta, no existe". El conocimiento en Google Docs, Slack o en la mente de las personas es invisible para el agente.

- [ ] **`docs/` no está estructurado como knowledge base del agente** — los docs existen pero no están organizados para divulgación progresiva. **Fix:** añadir `docs/design-docs/`, `docs/exec-plans/`, `docs/references/`.

- [ ] **Sin `docs/design-docs/core-beliefs.md`** — no hay un documento que capture los principios arquitectónicos fundamentales. **Fix:** crear con las decisiones de diseño del proyecto.

- [ ] **Sin tech-debt-tracker** — la deuda técnica no está versionada en el repositorio. **Fix:** `docs/exec-plans/tech-debt-tracker.md`.

- [ ] **Sin validación automática de la knowledge base** — los docs pueden quedar desactualizados sin que nadie lo note. **Fix:** añadir CI que verifique que los docs referenciados en `AGENTS.md` existen y tienen links válidos.

---

## 🟡 CI/CD Y CALIDAD

- [ ] **Sin pre-commit hooks** — `ruff`, `mypy`, tests unitarios no corren automáticamente antes de un commit. **Fix:** añadir `.pre-commit-config.yaml`.

- [ ] **Sin CI pipeline definido** — **Fix:** `.github/workflows/ci.yml` con lint + test + typecheck.

- [ ] **Sin coverage mínimo configurado** — los tests existen pero no hay umbral de cobertura. **Fix:** `[tool.pytest.ini_options]` con `--cov-fail-under=80`.

- [ ] **Sin mutation testing** — los tests pueden pasar sin detectar bugs reales. Martin Fowler menciona mutation testing como sensor de calidad subutilizado. **Fix:** añadir `mutmut` o `cosmic-ray`.

---

## 🟢 LONG-HORIZON Y MULTI-AGENTE

Para tareas complejas que no caben en una sesión.

- [ ] **Sin `InitializerAgent`** — no hay separación entre el agente que configura el entorno inicial y el que hace progreso incremental. Anthropic: este es el patrón para long-running tasks. **Fix:** `app/agents/initializer.py` + `app/agents/coder.py`.

- [ ] **Sin Ralph Loop** — cuando se agota el contexto, el agente para en lugar de reinyectar el prompt y continuar. LangChain: el Ralph Loop es el patrón para long-horizon work. **Fix:** hook en `AgentLoop` que detecta `finish_reason == "length"` y relanza.

- [ ] **Sin subagente spawning** — el agente no puede delegar subtareas. Todo lo hace en un único loop. **Fix:** `SpawnAgentTool` que instancia y ejecuta un sub-`AgentLoop`.

- [ ] **Sin agente de garbage collection** — el código generado por el agente puede acumular patrones subóptimos. OpenAI: un agente recurrente de "doc-gardening" / "cleanup" previene la entropía. **Fix:** script de limpieza recurrente.

---

## Conteo de gaps por categoría

| Categoría | Crítico | Alto | Medio | Bajo | Total |
|-----------|---------|------|-------|------|-------|
| Seguridad | 5 | — | — | — | **5** |
| Feedforward | — | 5 | — | — | **5** |
| Feedback sensors | — | 5 | — | — | **5** |
| Memoria/Estado | — | 5 | — | — | **5** |
| Context management | — | 4 | — | — | **4** |
| Arquitectura | — | 5 | — | — | **5** |
| Observabilidad | — | — | 4 | — | **4** |
| Knowledge base | — | — | 4 | — | **4** |
| CI/CD | — | — | 4 | — | **4** |
| Long-horizon | — | — | — | 4 | **4** |
| **TOTAL** | **5** | **24** | **12** | **4** | **45** |

---

## Ver también

- [ARCHITECTURE.md](ARCHITECTURE.md) — mapa del sistema actual
- [docs/exec-plans/PLAN.md](docs/exec-plans/PLAN.md) — fases de implementación priorizadas
