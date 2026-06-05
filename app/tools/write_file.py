"""This module defines the WriteFileTool, which allows agents to write content to files on the system.
This can be useful for tasks that require saving data, creating configuration files, or any other situation where the agent needs to persist information in a file.
"""

from typing import Any

from app.tools import Tool


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
