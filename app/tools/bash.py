"""This module defines the BashTerminalTool, which allows agents to execute bash commands and retrieve their output.
This can be useful for tasks that require interacting with the system, running scripts, or using command-line tools.
"""

from typing import Any

from app.tools import Tool


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
