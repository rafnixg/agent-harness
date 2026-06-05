"""This module defines the ReadFileTool, which allows agents to read the contents of files on the system.
This can be useful for tasks that require accessing data stored in files, such as configuration files,
logs, or any other text-based information.
"""

import os
from typing import Any

from app.tools import Tool


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
