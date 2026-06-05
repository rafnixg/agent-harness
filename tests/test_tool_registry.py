"""Tests for ToolRegistry and Tool base class (primary)."""

import pytest
from typing import Any

from app.tool import AllowList, AlwaysAllow, AskOnce, Tool, ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _SimpleTool(Tool):
    """Minimal concrete Tool for use in tests."""

    def __init__(self, name: str = "simple_tool", return_value: str = "ok"):
        self._name = name
        self._return_value = return_value

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A simple tool used for testing"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "An input string"},
            },
            "required": ["input"],
        }

    def execute(self, **kwargs: Any) -> str:
        return self._return_value


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class TestToolRegistryRegisterAndGet:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.tool = _SimpleTool()

    def test_register_allows_get(self):
        self.registry.register(self.tool)
        assert self.registry.get("simple_tool") is self.tool

    def test_get_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="Tool not found: missing"):
            self.registry.get("missing")

    def test_register_overwrites_existing_name(self):
        first = _SimpleTool(name="dup", return_value="first")
        second = _SimpleTool(name="dup", return_value="second")
        self.registry.register(first)
        self.registry.register(second)
        assert self.registry.get("dup") is second


class TestToolRegistryExecute:
    def setup_method(self):
        self.registry = ToolRegistry(permission_policy=AlwaysAllow())
        self.tool = _SimpleTool(return_value="result")
        self.registry.register(self.tool)

    def test_execute_known_tool(self):
        assert self.registry.execute("simple_tool", input="x") == "result"

    def test_execute_unknown_tool_raises_key_error(self):
        with pytest.raises(KeyError):
            self.registry.execute("ghost", input="x")


class TestPermissionPolicies:
    def test_allow_list_allows_configured_tool_without_prompt(self):
        registry = ToolRegistry(permission_policy=AllowList(names={"simple_tool"}))
        registry.register(_SimpleTool(return_value="ok"))
        assert registry.execute("simple_tool", input="x") == "ok"

    def test_allow_list_prompts_for_non_listed_tool(self, monkeypatch):
        registry = ToolRegistry(permission_policy=AllowList(names={"read_file"}))
        registry.register(_SimpleTool(return_value="ok"))
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert registry.execute("simple_tool", input="x") == "Tool execution cancelled by user."

    def test_ask_once_remembers_allow(self, monkeypatch):
        registry = ToolRegistry(permission_policy=AskOnce())
        registry.register(_SimpleTool(return_value="ok"))
        prompt_calls = {"count": 0}

        def _fake_input(_prompt: str) -> str:
            prompt_calls["count"] += 1
            return "y"

        monkeypatch.setattr("builtins.input", _fake_input)
        assert registry.execute("simple_tool", input="a") == "ok"
        assert registry.execute("simple_tool", input="b") == "ok"
        assert prompt_calls["count"] == 1

    def test_ask_once_remembers_deny(self, monkeypatch):
        registry = ToolRegistry(permission_policy=AskOnce())
        registry.register(_SimpleTool(return_value="ok"))
        prompt_calls = {"count": 0}

        def _fake_input(_prompt: str) -> str:
            prompt_calls["count"] += 1
            return "n"

        monkeypatch.setattr("builtins.input", _fake_input)
        assert registry.execute("simple_tool", input="a") == "Tool execution cancelled by user."
        assert registry.execute("simple_tool", input="b") == "Tool execution cancelled by user."
        assert prompt_calls["count"] == 1


class TestToolRegistryLen:
    def test_empty_registry_len_is_zero(self):
        assert len(ToolRegistry()) == 0

    def test_len_increases_with_each_registration(self):
        registry = ToolRegistry()
        registry.register(_SimpleTool(name="t1"))
        assert len(registry) == 1
        registry.register(_SimpleTool(name="t2"))
        assert len(registry) == 2

    def test_overwrite_does_not_increase_len(self):
        registry = ToolRegistry()
        registry.register(_SimpleTool(name="dup"))
        registry.register(_SimpleTool(name="dup"))
        assert len(registry) == 1


class TestToolRegistryIter:
    def test_iterates_registered_tools(self):
        registry = ToolRegistry()
        t1 = _SimpleTool(name="a")
        t2 = _SimpleTool(name="b")
        registry.register(t1)
        registry.register(t2)
        tools = list(registry)
        assert t1 in tools
        assert t2 in tools

    def test_empty_registry_iterates_nothing(self):
        assert list(ToolRegistry()) == []


class TestToolRegistryToOpenAISchema:
    def test_schema_list_length_matches_registered_tools(self):
        registry = ToolRegistry()
        registry.register(_SimpleTool(name="t1"))
        registry.register(_SimpleTool(name="t2"))
        assert len(registry.to_openai_schema()) == 2

    def test_empty_registry_returns_empty_list(self):
        assert ToolRegistry().to_openai_schema() == []

    def test_schema_contains_correct_structure(self):
        registry = ToolRegistry()
        registry.register(_SimpleTool(name="my_tool"))
        schema = registry.to_openai_schema()[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "my_tool"
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]


# ---------------------------------------------------------------------------
# Tool.to_openai_schema (base class method)
# ---------------------------------------------------------------------------

class TestToolToOpenAISchema:
    def test_schema_shape(self):
        tool = _SimpleTool()
        schema = tool.to_openai_schema()
        assert schema == {
            "type": "function",
            "function": {
                "name": "simple_tool",
                "description": "A simple tool used for testing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "An input string"},
                    },
                    "required": ["input"],
                },
            },
        }

    def test_schema_name_reflects_tool_name(self):
        tool = _SimpleTool(name="custom_name")
        assert tool.to_openai_schema()["function"]["name"] == "custom_name"
