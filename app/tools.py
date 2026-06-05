"""Concrete tool implementations."""

import os
from typing import Any

from app.tool import PermissionPolicy, Tool, ToolRegistry


class ReadFileTool(Tool):
    """Tool to read file contents."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read and return the contents of a file"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read",
                }
            },
            "required": ["file_path"],
        }

    def execute(self, **kwargs) -> str:
        file_path = kwargs["file_path"]
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


class WriteFileTool(Tool):
    """Tool to write content to a file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path of the file to write to",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    def execute(self, **kwargs) -> str:
        file_path = kwargs["file_path"]
        content = kwargs["content"]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"

class BashTerminalTool(Tool):
    """Tool to execute bash commands."""

    @property
    def name(self) -> str:
        return "bash_terminal"

    @property
    def description(self) -> str:
        return "Execute a bash command and return the output"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                }
            },
            "required": ["command"],
        }

    def execute(self, **kwargs) -> str:
        import subprocess

        command = kwargs["command"]
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Command failed with error: {e.stderr}"

def create_default_registry(
    permission_policy: PermissionPolicy | None = None,
) -> ToolRegistry:
    """Create a registry with all default tools."""
    registry = ToolRegistry(permission_policy=permission_policy)
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(BashTerminalTool())
    return registry
