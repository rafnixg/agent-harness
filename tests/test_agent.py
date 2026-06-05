"""Tests for AgentLoop (primary)."""

import io
import json
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from app.agent import AgentLoop
from app.tools import Tool, ToolRegistry
from app.tools.permission_policy import AlwaysAllow
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content: str | None = None, tool_calls: list | None = None):
    """Build a mock LLM response object."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_call(name: str, arguments: dict, call_id: str = "call_1"):
    """Build a mock tool_call object (function type)."""
    tc = MagicMock()
    tc.type = "function"
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


class _EchoTool(Tool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes input back"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }

    def execute(self, **kwargs: Any) -> str:
        return kwargs["text"]


# ---------------------------------------------------------------------------
# AgentLoop initialisation
# ---------------------------------------------------------------------------

class TestAgentLoopInit:
    def test_uses_explicit_model(self):
        provider = MagicMock()
        agent = AgentLoop(llm_provider=provider, workspace=Path("/tmp"), model="explicit-model")
        assert agent.model == "explicit-model"

    def test_falls_back_to_provider_default_model(self):
        provider = MagicMock()
        provider.get_default_model.return_value = "provider-default"
        agent = AgentLoop(llm_provider=provider, workspace=Path("/tmp"))
        assert agent.model == "provider-default"

    def test_workspace_stored(self):
        provider = MagicMock()
        ws = Path("/some/workspace")
        agent = AgentLoop(llm_provider=provider, workspace=ws, model="m")
        assert agent.workspace == ws

    def test_starts_with_empty_messages(self):
        agent = AgentLoop(llm_provider=MagicMock(), workspace=Path("/tmp"), model="m")
        assert agent.messages == []

    def test_creates_internal_tool_registry(self):
        agent = AgentLoop(llm_provider=MagicMock(), workspace=Path("/tmp"), model="m")
        assert isinstance(agent.tools, ToolRegistry)


# ---------------------------------------------------------------------------
# AgentLoop.run — happy path
# ---------------------------------------------------------------------------

class TestAgentLoopRun:
    def setup_method(self):
        self.provider = MagicMock()
        self.agent = AgentLoop(
            llm_provider=self.provider,
            workspace=Path("/tmp"),
            model="test-model",
        )
        self.agent.tools = ToolRegistry(permission_policy=AlwaysAllow())

    def test_returns_content_when_no_tool_calls(self):
        self.provider.chat.completions.create.return_value = _make_response(content="Hello!")
        assert self.agent.run("say hello") == "Hello!"

    def test_returns_empty_string_for_none_content(self):
        self.provider.chat.completions.create.return_value = _make_response(content=None)
        assert self.agent.run("prompt") == ""

    def test_initialises_messages_with_user_prompt(self):
        self.provider.chat.completions.create.return_value = _make_response(content="ok")
        self.agent.run("my prompt")
        assert self.agent.messages[0] == {"role": "user", "content": "my prompt"}

    def test_resets_messages_on_each_run(self):
        self.provider.chat.completions.create.return_value = _make_response(content="ok")
        self.agent.run("first run")
        self.agent.run("second run")
        assert self.agent.messages[0] == {"role": "user", "content": "second run"}

    def test_raises_when_no_choices_in_response(self):
        response = MagicMock()
        response.choices = []
        self.provider.chat.completions.create.return_value = response
        with pytest.raises(RuntimeError, match="No choices in response"):
            self.agent.run("prompt")

    def test_calls_chat_with_correct_model_and_max_tokens(self):
        self.provider.chat.completions.create.return_value = _make_response(content="done")
        self.agent.run("prompt")
        call_kwargs = self.provider.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["max_tokens"] == 4000

    def test_run_with_single_tool_call_then_final_response(self):
        """Agent should call tool, then make a second LLM call and return final answer."""
        self.agent.tools.register(_EchoTool())
        tc = _make_tool_call("echo", {"text": "world"})
        first = _make_response(tool_calls=[tc])
        second = _make_response(content="Final answer")
        self.provider.chat.completions.create.side_effect = [first, second]

        with redirect_stderr(io.StringIO()):
            result = self.agent.run("use echo")

        assert result == "Final answer"
        assert self.provider.chat.completions.create.call_count == 2

    def test_tool_result_appended_to_messages(self):
        self.agent.tools.register(_EchoTool())
        tc = _make_tool_call("echo", {"text": "ping"}, call_id="cid_1")
        first = _make_response(tool_calls=[tc])
        second = _make_response(content="done")
        self.provider.chat.completions.create.side_effect = [first, second]

        with redirect_stderr(io.StringIO()):
            self.agent.run("test")

        tool_messages = [m for m in self.agent.messages if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert tool_messages[0]["tool_call_id"] == "cid_1"
        assert tool_messages[0]["content"] == "ping"


# ---------------------------------------------------------------------------
# AgentLoop._handle_tool_calls
# ---------------------------------------------------------------------------

class TestAgentLoopHandleToolCalls:
    def setup_method(self):
        self.agent = AgentLoop(
            llm_provider=MagicMock(),
            workspace=Path("/tmp"),
            model="m",
        )
        self.agent.tools = ToolRegistry(permission_policy=AlwaysAllow())

    def test_unknown_tool_call_type_is_skipped(self):
        tc = MagicMock()
        tc.type = "unknown_type"
        with redirect_stderr(io.StringIO()):
            self.agent._handle_tool_calls([tc])
        assert self.agent.messages == []

    def test_function_tool_call_appends_result_message(self):
        self.agent.tools.register(_EchoTool())
        tc = _make_tool_call("echo", {"text": "hello"}, call_id="c1")
        with redirect_stderr(io.StringIO()):
            self.agent._handle_tool_calls([tc])
        assert len(self.agent.messages) == 1
        msg = self.agent.messages[0]
        assert msg["role"] == "tool"
        assert msg["tool_call_id"] == "c1"
        assert msg["content"] == "hello"

    def test_tool_error_is_captured_as_string(self):
        """Tool errors should not propagate; they become error strings."""
        broken = MagicMock(spec=Tool)
        broken.name = "broken"
        broken.execute.side_effect = FileNotFoundError("not found")
        self.agent.tools.register(broken)

        tc = _make_tool_call("broken", {}, call_id="err1")
        with redirect_stderr(io.StringIO()):
            self.agent._handle_tool_calls([tc])

        assert self.agent.messages[0]["content"] == "Error: not found"

    def test_multiple_tool_calls_all_appended(self):
        self.agent.tools.register(_EchoTool())
        tc1 = _make_tool_call("echo", {"text": "a"}, call_id="c1")
        tc2 = _make_tool_call("echo", {"text": "b"}, call_id="c2")
        with redirect_stderr(io.StringIO()):
            self.agent._handle_tool_calls([tc1, tc2])
        assert len(self.agent.messages) == 2
        assert self.agent.messages[0]["content"] == "a"
        assert self.agent.messages[1]["content"] == "b"

    def test_key_error_on_missing_tool_is_captured(self):
        tc = _make_tool_call("nonexistent", {}, call_id="c1")
        with redirect_stderr(io.StringIO()):
            self.agent._handle_tool_calls([tc])
        assert self.agent.messages[0]["content"].startswith("Error:")


# ---------------------------------------------------------------------------
# AgentLoop.max_iterations
# ---------------------------------------------------------------------------

class TestAgentLoopMaxIterations:
    def test_default_max_iterations_is_40(self):
        agent = AgentLoop(llm_provider=MagicMock(), workspace=Path("/tmp"), model="m")
        assert agent.max_iterations == 40

    def test_custom_max_iterations_stored(self):
        agent = AgentLoop(
            llm_provider=MagicMock(), workspace=Path("/tmp"), model="m", max_iterations=5
        )
        assert agent.max_iterations == 5

    def test_raises_runtime_error_when_limit_reached(self):
        """Agent raises RuntimeError instead of looping forever."""
        provider = MagicMock()
        agent = AgentLoop(
            llm_provider=provider,
            workspace=Path("/tmp"),
            model="m",
            max_iterations=3,
        )
        agent.tools = ToolRegistry(permission_policy=AlwaysAllow())
        agent.tools.register(_EchoTool())
        tc = _make_tool_call("echo", {"text": "ping"})
        # LLM always returns a tool call — never a final answer
        provider.chat.completions.create.return_value = _make_response(tool_calls=[tc])

        with pytest.raises(RuntimeError, match="max_iterations reached: 3"):
            with redirect_stderr(io.StringIO()):
                agent.run("loop forever")

    def test_tool_called_exactly_max_iterations_times(self):
        """The tool is executed once per iteration before the limit fires."""
        provider = MagicMock()
        agent = AgentLoop(
            llm_provider=provider,
            workspace=Path("/tmp"),
            model="m",
            max_iterations=4,
        )
        agent.tools = ToolRegistry(permission_policy=AlwaysAllow())
        counter_tool = _EchoTool()
        agent.tools.register(counter_tool)
        tc = _make_tool_call("echo", {"text": "x"})
        provider.chat.completions.create.return_value = _make_response(tool_calls=[tc])

        with pytest.raises(RuntimeError):
            with redirect_stderr(io.StringIO()):
                agent.run("loop")

        assert provider.chat.completions.create.call_count == 4

    def test_error_message_includes_iteration_count(self):
        provider = MagicMock()
        agent = AgentLoop(
            llm_provider=provider,
            workspace=Path("/tmp"),
            model="m",
            max_iterations=7,
        )
        agent.tools.register(_EchoTool())
        tc = _make_tool_call("echo", {"text": "x"})
        provider.chat.completions.create.return_value = _make_response(tool_calls=[tc])

        with pytest.raises(RuntimeError, match="7"):
            with redirect_stderr(io.StringIO()):
                agent.run("loop")

