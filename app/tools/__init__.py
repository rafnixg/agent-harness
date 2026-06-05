"""Tools are a way for agents to interact with the world outside of their own code. 
They can be used to access APIs, run commands, read and write files, and more.
This module contains the base Tool class, as well as some default tools like Bash.
"""

from app.tools.base import ToolRegistry, Tool
from app.tools.permission_policy import PermissionPolicy
from app.tools.bash import BashTerminalTool
from app.tools.read_file import ReadFileTool
from app.tools.write_file import WriteFileTool

def create_default_registry(
    permission_policy: PermissionPolicy | None = None,
) -> ToolRegistry:
    """Create a registry with all default tools."""
    registry = ToolRegistry(permission_policy=permission_policy)
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(BashTerminalTool())
    return registry
