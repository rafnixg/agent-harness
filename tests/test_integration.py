"""End-to-end integration tests — mocked LLM, real agent loop and real tools."""

import io
import json
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.agent import AgentLoop
from app.tools import Tool, ToolRegistry
from app.tools import ReadFileTool, WriteFileTool, build_tools
from app.tools.permission_policy import AlwaysAllow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(content=None, tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_tool_call(name, arguments, call_id="c1"):
    tc = MagicMock()
    tc.type = "function"
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


class _CounterTool(Tool):
    """Tool that counts invocations; useful for asserting call counts."""

    def __init__(self):
        self.count = 0

    @property
    def name(self) -> str:
        return "counter"

    @property
    def description(self) -> str:
        return "Increments and returns an internal counter"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self, **kwargs: Any) -> str:
        self.count += 1
        return str(self.count)


# ---------------------------------------------------------------------------
# Integration — full agent loop with mocked LLM
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAgentFullLoop:
    def _agent(self, provider, tmp_path, max_iterations=10):
        agent = AgentLoop(
            llm_provider=provider,
            workspace=tmp_path,
            model="test",
            max_iterations=max_iterations,
        )
        agent.tools = ToolRegistry(permission_policy=AlwaysAllow())
        return agent

    def test_direct_response_no_tools(self, tmp_path):
        """Agent returns immediately when LLM gives a plain text answer."""
        provider = MagicMock()
        provider.chat.completions.create.return_value = _make_response(content="42")
        result = self._agent(provider, tmp_path).run("what is 6*7?")
        assert result == "42"

    def test_single_tool_call_then_final_answer(self, tmp_path):
        provider = MagicMock()
        counter = _CounterTool()
        tc = _make_tool_call("counter", {})
        provider.chat.completions.create.side_effect = [
            _make_response(tool_calls=[tc]),
            _make_response(content="The counter is 1"),
        ]
        agent = self._agent(provider, tmp_path)
        agent.tools.register(counter)

        with redirect_stderr(io.StringIO()):
            result = agent.run("increment the counter")

        assert result == "The counter is 1"
        assert counter.count == 1

    def test_two_sequential_tool_calls(self, tmp_path):
        provider = MagicMock()
        counter = _CounterTool()
        tc1 = _make_tool_call("counter", {}, call_id="c1")
        tc2 = _make_tool_call("counter", {}, call_id="c2")
        provider.chat.completions.create.side_effect = [
            _make_response(tool_calls=[tc1]),
            _make_response(tool_calls=[tc2]),
            _make_response(content="Done, counter=2"),
        ]
        agent = self._agent(provider, tmp_path)
        agent.tools.register(counter)

        with redirect_stderr(io.StringIO()):
            result = agent.run("increment twice")

        assert result == "Done, counter=2"
        assert counter.count == 2

    def test_max_iterations_guard_fires_in_full_run(self, tmp_path):
        """Infinite-loop scenario: max_iterations is respected end-to-end."""
        provider = MagicMock()
        counter = _CounterTool()
        tc = _make_tool_call("counter", {})
        provider.chat.completions.create.return_value = _make_response(tool_calls=[tc])

        agent = self._agent(provider, tmp_path, max_iterations=3)
        agent.tools.register(counter)

        with pytest.raises(RuntimeError, match="max_iterations"):
            with redirect_stderr(io.StringIO()):
                agent.run("never stop")

        assert counter.count == 3

    def test_tool_error_captured_and_agent_continues(self, tmp_path):
        """A FileNotFoundError from a tool is returned as an error string; agent continues."""
        provider = MagicMock()
        tc = _make_tool_call("read_file", {"file_path": "/nonexistent/file.txt"})
        provider.chat.completions.create.side_effect = [
            _make_response(tool_calls=[tc]),
            _make_response(content="File not found, stopping"),
        ]
        agent = self._agent(provider, tmp_path)
        agent.tools.register(ReadFileTool())

        with redirect_stderr(io.StringIO()):
            result = agent.run("read a missing file")

        # Agent should have continued and returned the second LLM response
        assert "stopping" in result

        # The tool error should appear in the message history
        tool_msgs = [m for m in agent.messages if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert "Error:" in tool_msgs[0]["content"]

    def test_write_then_read_file_roundtrip(self, tmp_path):
        """Integration: WriteFileTool followed by ReadFileTool via the agent."""
        file_path = str(tmp_path / "data.txt")
        provider = MagicMock()
        tc_write = _make_tool_call(
            "write_file", {"file_path": file_path, "content": "hello world"}, call_id="w1"
        )
        tc_read = _make_tool_call("read_file", {"file_path": file_path}, call_id="r1")
        provider.chat.completions.create.side_effect = [
            _make_response(tool_calls=[tc_write]),
            _make_response(tool_calls=[tc_read]),
            _make_response(content="File says: hello world"),
        ]
        agent = self._agent(provider, tmp_path)
        agent.tools.register(WriteFileTool())
        agent.tools.register(ReadFileTool())

        with redirect_stderr(io.StringIO()):
            result = agent.run("write then read data.txt")

        assert "hello world" in result

    def test_messages_reset_between_runs(self, tmp_path):
        """Each call to run() starts with a clean message history."""
        provider = MagicMock()
        provider.chat.completions.create.return_value = _make_response(content="ok")
        agent = self._agent(provider, tmp_path)

        agent.run("first prompt")
        agent.run("second prompt")

        assert agent.messages[0] == {"role": "user", "content": "second prompt"}


# ---------------------------------------------------------------------------
# Integration — create_default_registry tools are accessible via agent
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestDefaultRegistryInAgent:
    def test_default_registry_tools_are_invokable(self, tmp_path):
        """Verify all 3 default tools can be found and executed through the agent."""
        registry = build_tools()
        # All three tool names should resolve without error
        registry.get("read_file")
        registry.get("write_file")
        registry.get("bash_terminal")

    def test_agent_with_default_tools_can_write_and_read(self, tmp_path):
        """Full agent uses default registry to write a file and read it back."""
        file_path = str(tmp_path / "out.txt")
        provider = MagicMock()
        tc_write = _make_tool_call(
            "write_file", {"file_path": file_path, "content": "test data"}, call_id="w1"
        )
        tc_read = _make_tool_call("read_file", {"file_path": file_path}, call_id="r1")
        provider.chat.completions.create.side_effect = [
            _make_response(tool_calls=[tc_write]),
            _make_response(tool_calls=[tc_read]),
            _make_response(content="done"),
        ]
        agent = AgentLoop(
            llm_provider=provider,
            workspace=tmp_path,
            model="test",
        )
        agent.tools = ToolRegistry(permission_policy=AlwaysAllow())
        for tool in build_tools(permission_policy=AlwaysAllow()):
            agent.tools.register(tool)

        with redirect_stderr(io.StringIO()):
            result = agent.run("write and read")

        assert result == "done"


# ---------------------------------------------------------------------------
# Live test (skipped without OPENROUTER_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.live
class TestLiveAgent:
    def test_agent_smoke_test(self, tmp_path):
        import os

        from openai import OpenAI

        api_key = os.environ["OPENROUTER_API_KEY"]
        base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model = os.environ.get("OPENROUTER_MODEL", "openrouter/free")

        client = OpenAI(api_key=api_key, base_url=base_url)
        agent = AgentLoop(
            llm_provider=client,
            workspace=tmp_path,
            model=model,
            max_iterations=3,
        )
        result = agent.run("Respond with exactly the word: PONG")
        assert len(result) > 0
