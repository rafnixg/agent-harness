# Documentacion

Este sitio contiene la documentacion del proyecto **AI Coding Agent Harness**.

## Secciones

- [Introduccion](introduccion.md)
- [Agent Loop](agent-loop.md)
- [Providers](providers.md)
- [Tools basicas](tools-basicas.md)
- [Permisos](permisos.md)

## Uso local

```bash
uv sync --all-extras
uv run mkdocs serve
```

Generar HTML estatico:

```bash
uv run mkdocs build
```

El resultado queda en `site/`.
