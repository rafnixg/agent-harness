"""Agent class that implements the conversation loop."""

import json
import sys

from pathlib import Path
from openai import OpenAI

from app.tool import ToolRegistry
from app.providers.base import LLMProvider


class AgentLoop:
    """AI Agent that can use tools to accomplish tasks."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 40,
        max_tokens: int = 4000,
    ) -> None:
        self.llm_provider = llm_provider
        self.workspace = workspace
        self.model = model or llm_provider.get_default_model()
        self.max_tokens = max_tokens
        self.max_iterations = max_iterations
        self.messages: list = []
        self._last_usage: dict[str, int] = {}

        self.tools = ToolRegistry()

    def run(self, prompt: str) -> str:
        """Run the agent with a user prompt and return the final response."""
        self.messages = [{"role": "user", "content": prompt}]

        for _iteration in range(self.max_iterations):
            response = self._chat()

            if not response.choices:
                raise RuntimeError("No choices in response")

            message = response.choices[0].message
            self.messages.append(message)

            # Check if done (no tool calls)
            if not message.tool_calls:
                return message.content or ""

            # Handle tool calls
            self._handle_tool_calls(message.tool_calls)

        raise RuntimeError(f"max_iterations reached: {self.max_iterations}")

    def _chat(self):
        """Make a chat completion request."""
        return self.llm_provider.chat.completions.create(
            model=self.model,
            messages=self.messages,  # type: ignore[arg-type]
            tools=self.tools.to_openai_schema(),  # type: ignore[arg-type]
            max_tokens=self.max_tokens,
        )

    def _handle_tool_calls(self, tool_calls) -> None:
        """Execute tool calls and add results to messages."""
        for tool_call in tool_calls:
            if tool_call.type != "function":
                print(f"Unknown tool call type: {tool_call.type}", file=sys.stderr)
                continue

            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            try:
                result = self.tools.execute(name, **args)
            except (KeyError, FileNotFoundError, ValueError, OSError) as e:
                result = f"Error: {e}"

            print(
                f"Tool call: {name}({tool_call.function.arguments}) -> {result}",
                file=sys.stderr,
            )

            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )
