# Documentacion

Este sitio contiene la documentacion del proyecto **AI Coding Agent Harness**.

## Que es este proyecto

Este repositorio implementa un agente de codificacion que combina:

- razonamiento con un LLM
- ejecucion de herramientas reales (lectura/escritura de archivos y terminal)
- control operativo mediante politicas de permisos

El objetivo es ofrecer un harness simple, extensible y facil de entender para experimentar con patrones tipo ReAct y function calling.

## Para quien es esta documentacion

- Si quieres usar el agente por CLI o por API HTTP.
- Si quieres extender tools o providers.
- Si quieres contribuir en arquitectura, seguridad o testeo.

## Inicio rapido

1. Lee [Introduccion](introduccion.md) para entender arquitectura y flujo general.
2. Revisa [Arquitectura](architecture.md) para entender capas y responsabilidades.
3. Revisa [API HTTP](api.md) para integrar el agente por endpoint.
4. Consulta [Permisos](permisos.md) antes de habilitar tools en entornos compartidos.

## Arranque rapido

### CLI

```bash
uv sync --all-extras
uv run -m app.main -p "Lee README.md y dame un resumen corto"
```

### API HTTP

```bash
uv run -m app.server --host 127.0.0.1 --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/ask \
	-H "Content-Type: application/json" \
	-d '{"prompt": "Resume el proyecto"}'
```

## Rutas recomendadas de lectura

### Ruta 1: Integracion rapida

1. [API HTTP](api.md)
2. [Permisos](permisos.md)
3. [Providers](providers.md)

### Ruta 2: Entender el nucleo tecnico

1. [Arquitectura](architecture.md)
2. [Agent Loop](agent-loop.md)
3. [Tools basicas](tools-basicas.md)

### Ruta 3: Empezar a contribuir

1. [Introduccion](introduccion.md)
2. [Arquitectura](architecture.md)
3. [Permisos](permisos.md)

## Secciones

- [Introduccion](introduccion.md)
- [Arquitectura](architecture.md)
- [API HTTP](api.md)
- [Agent Loop](agent-loop.md)
- [Providers](providers.md)
- [Tools basicas](tools-basicas.md)
- [Permisos](permisos.md)

## Calidad y validacion

Para validar cambios de documentacion:

```bash
uv run mkdocs build
```

Para validar cambios de codigo:

```bash
uv run -m pytest tests/ -q
```

## Proximos pasos sugeridos

- Agregar una seccion de ejemplos de prompts por caso de uso.
- Incluir una guia de troubleshooting de configuracion (`API key`, provider, permisos).
- Documentar un flujo recomendado para publicar la documentacion en Pages.
