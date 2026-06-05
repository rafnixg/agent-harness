# Tools básicas

Las tools son las acciones que el agente puede ejecutar. Cada una encapsula una operación del sistema y expone un esquema JSON para que el LLM sepa cómo invocarla.

---

## Arquitectura base

### Clase `Tool` (ABC)

```
app/tool.py
```

Todo tool hereda de `Tool` e implementa cuatro miembros abstractos:

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...          # identificador único

    @property
    @abstractmethod
    def description(self) -> str: ...   # descripción para el LLM

    @property
    @abstractmethod
    def parameters(self) -> dict: ...   # JSON Schema de los parámetros

    @abstractmethod
    def execute(self, **kwargs) -> str: ...  # lógica de ejecución
```

El método concreto `to_openai_schema()` convierte el tool al formato que espera la API de OpenAI:

```python
{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read and return the contents of a file",
        "parameters": { ... }
    }
}
```

### Clase `ToolRegistry`

```
app/tool.py
```

Contenedor que almacena tools por nombre y los expone al agente:

| Método | Descripción |
|---|---|
| `register(tool)` | Registra un tool |
| `get(name)` | Obtiene un tool por nombre; lanza `KeyError` si no existe |
| `execute(name, **kwargs)` | Ejecuta un tool por nombre |
| `to_openai_schema()` | Devuelve lista de schemas para la API |
| `__len__()` | Número de tools registrados |
| `__iter__()` | Iteración sobre los tools |

`ToolRegistry` ahora delega decisiones de autorización a `PermissionPolicy`.

Flujo:

```text
agent loop -> permission policy -> registry.execute
```

### `PermissionPolicy`

```
app/tool.py
```

Interfaz:

```python
class PermissionPolicy(ABC):
    def decide(self, name: str, tool_input: dict[str, Any]) -> PermissionDecision:
        ...  # "allow" | "deny" | "ask"
```

Implementaciones incluidas:

| Política | Comportamiento |
|---|---|
| `AlwaysAsk` | Pregunta en cada tool call |
| `AlwaysAllow` | Ejecuta sin preguntar |
| `AllowList(names)` | Permite tools listadas, pregunta el resto |
| `AskOnce` | Pregunta una vez por tool y recuerda la decisión en la sesión |

---

## Tools incluidas

### `read_file`

**Clase**: `ReadFileTool` (`app/tools.py`)

Lee y devuelve el contenido completo de un archivo de texto.

**Parámetros**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `file_path` | `string` | Ruta al archivo a leer |

**Comportamiento**

- Abre el archivo con encoding `utf-8`.
- Lanza `FileNotFoundError` si la ruta no existe (el agente captura el error y lo incluye como contexto en la próxima iteración).

**Ejemplo de invocación por el LLM**

```json
{
  "name": "read_file",
  "arguments": { "file_path": "/home/user/proyecto/main.py" }
}
```

**Retorno**: contenido del archivo como string.

---

### `write_file`

**Clase**: `WriteFileTool` (`app/tools.py`)

Escribe contenido a un archivo. Si el archivo no existe lo crea; si existe lo sobreescribe.

**Parámetros**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `file_path` | `string` | Ruta del archivo destino |
| `content` | `string` | Contenido a escribir |

**Comportamiento**

- Abre el archivo en modo escritura (`"w"`) con encoding `utf-8`.
- Crea directorios intermedios _no_ los crea automáticamente — el directorio padre debe existir.

**Ejemplo de invocación por el LLM**

```json
{
  "name": "write_file",
  "arguments": {
    "file_path": "/home/user/proyecto/output.txt",
    "content": "resultado del análisis..."
  }
}
```

**Retorno**: `"Successfully wrote to <file_path>"`.

---

### `bash_terminal`

**Clase**: `BashTerminalTool` (`app/tools.py`)

Ejecuta un comando de shell y devuelve su salida estándar.

**Parámetros**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `command` | `string` | Comando a ejecutar |

**Comportamiento**

- Usa `subprocess.run(..., shell=True, check=True, capture_output=True, text=True)`.
- En caso de error (`CalledProcessError`), devuelve `"Command failed with error: <stderr>"` en lugar de lanzar excepción.
- La salida stderr del proceso exitoso se descarta (solo se devuelve stdout).

> **Nota de seguridad**: este tool no aplica ningún filtro sobre el comando. Ver [Permisos](permisos.md) para consideraciones de seguridad.

**Ejemplo de invocación por el LLM**

```json
{
  "name": "bash_terminal",
  "arguments": { "command": "find . -name '*.py' | wc -l" }
}
```

**Retorno**: stdout del comando como string.

---

## `create_default_registry()`

Función de conveniencia que devuelve un `ToolRegistry` pre-cargado con los tres tools anteriores.
Acepta opcionalmente una `PermissionPolicy`:

```python
from app.tools import create_default_registry
from app.tool import AskOnce

registry = create_default_registry(permission_policy=AskOnce())
# registry tiene: read_file, write_file, bash_terminal
```

Usada en `main.py` para configurar el agente por defecto.

---

## Crear un tool personalizado

1. Heredar de `Tool` en `app/tools.py` (o en un archivo nuevo).
2. Implementar `name`, `description`, `parameters` y `execute`.
3. Registrarlo en `create_default_registry()` o directamente en `agent.tools`.

**Ejemplo mínimo**

```python
from typing import Any
from app.tool import Tool

class ListDirectoryTool(Tool):
    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and folders in a directory"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"}
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> str:
        import os
        entries = os.listdir(kwargs["path"])
        return "\n".join(entries)
```

```python
# Registrar manualmente
agent.tools.register(ListDirectoryTool())
```
