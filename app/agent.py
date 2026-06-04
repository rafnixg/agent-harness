"""Agent class that implements the conversation loop."""

import asyncio
import json
import sys

from pathlib import Path
from typing import Any

from app.tool import ToolRegistry
from app.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class AgentLoop:
    """AI Agent that can use tools to accomplish tasks."""

    def __init__(
        self,
        llm_provider: Any,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 40,
        max_tokens: int = 4000,
    ) -> None:
        self.llm_provider = llm_provider
        self.workspace = workspace
        self.model = model or self._get_provider_default_model()
        self.max_tokens = max_tokens
        self.max_iterations = max_iterations
        self.messages: list = []
        self._last_usage: dict[str, int] = {}

        self.tools = ToolRegistry()

    def _get_provider_default_model(self) -> str:
        """Resolve default model from provider object if available."""
        get_model = getattr(self.llm_provider, "get_default_model", None)
        if callable(get_model):
            return get_model()
        raise RuntimeError("A model must be provided when provider has no default model")

    @staticmethod
    def _run_async(coro):
        """Run async provider call from sync loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        # Fallback for nested-loop contexts (e.g., notebook tests).
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def _uses_structured_provider(self) -> bool:
        """Whether provider follows the LLMProvider interface."""
        return isinstance(self.llm_provider, LLMProvider)

    def run(self, prompt: str) -> str:
        """Run the agent with a user prompt and return the final response."""
        self.messages = [{"role": "user", "content": prompt}]

        for _iteration in range(self.max_iterations):
            response = self._chat()

            if self._uses_structured_provider():
                llm_response = response
                if llm_response.finish_reason == "error":
                    raise RuntimeError(llm_response.content or "LLM provider error")

                self._append_structured_assistant_message(llm_response)
                if not llm_response.has_tool_calls:
                    return llm_response.content or ""

                self._handle_tool_calls(llm_response.tool_calls)
                continue

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
        if self._uses_structured_provider():
            return self._run_async(
                self.llm_provider.chat_with_retry(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools.to_openai_schema(),
                    max_tokens=self.max_tokens,
                )
            )

        return self.llm_provider.chat.completions.create(
            model=self.model,
            messages=self.messages,  # type: ignore[arg-type]
            tools=self.tools.to_openai_schema(),  # type: ignore[arg-type]
            max_tokens=self.max_tokens,
        )

    def _append_structured_assistant_message(self, response: LLMResponse) -> None:
        """Append an assistant turn from provider-agnostic LLMResponse."""
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.content,
        }
        if response.tool_calls:
            msg["tool_calls"] = [tc.to_openai_tool_call() for tc in response.tool_calls]
        self.messages.append(msg)

    @staticmethod
    def _extract_tool_call(tc: Any) -> tuple[str, str, str, dict[str, Any]]:
        """Normalize tool call object from provider-specific formats."""
        if isinstance(tc, ToolCallRequest):
            return "function", tc.id, tc.name, tc.arguments

        if isinstance(tc, dict):
            call_type = str(tc.get("type", "function"))
            call_id = str(tc.get("id", ""))
            function = tc.get("function") or {}
            name = str(function.get("name", ""))
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            return call_type, call_id, name, arguments

        call_type = getattr(tc, "type", "function")
        call_id = getattr(tc, "id", "")
        function = getattr(tc, "function", None)
        name = getattr(function, "name", "") if function else ""
        arguments = getattr(function, "arguments", "{}") if function else {}
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        return call_type, call_id, name, arguments

    def _handle_tool_calls(self, tool_calls) -> None:
        """Execute tool calls and add results to messages."""
        for tool_call in tool_calls:
            tc_type, tc_id, name, args = self._extract_tool_call(tool_call)

            if tc_type != "function":
                print(f"Unknown tool call type: {tc_type}", file=sys.stderr)
                continue

            try:
                result = self.tools.execute(name, **args)
            except (KeyError, FileNotFoundError, ValueError, OSError) as e:
                result = f"Error: {e}"

            print(
                f"Tool call: {name}({json.dumps(args, ensure_ascii=False)}) -> {result}",
                file=sys.stderr,
            )

            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result,
                }
            )
