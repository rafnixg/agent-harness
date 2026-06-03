"""Tests for providers/base.py data classes and static helpers (secondary)."""

import pytest

from app.providers.base import GenerationSettings, LLMProvider, LLMResponse, ToolCallRequest


# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------

class TestLLMResponse:
    def test_has_tool_calls_false_when_no_tool_calls(self):
        assert LLMResponse(content="hello").has_tool_calls is False

    def test_has_tool_calls_true_when_tool_calls_present(self):
        tc = ToolCallRequest(id="1", name="tool", arguments={})
        assert LLMResponse(content=None, tool_calls=[tc]).has_tool_calls is True

    def test_default_finish_reason_is_stop(self):
        assert LLMResponse(content="x").finish_reason == "stop"

    def test_default_tool_calls_is_empty_list(self):
        assert LLMResponse(content="x").tool_calls == []

    def test_default_usage_is_empty_dict(self):
        assert LLMResponse(content="x").usage == {}

    def test_default_reasoning_content_is_none(self):
        assert LLMResponse(content="x").reasoning_content is None

    def test_default_thinking_blocks_is_none(self):
        assert LLMResponse(content="x").thinking_blocks is None

    def test_content_can_be_none(self):
        assert LLMResponse(content=None).content is None


# ---------------------------------------------------------------------------
# ToolCallRequest
# ---------------------------------------------------------------------------

class TestToolCallRequest:
    def _make(self, **overrides):
        defaults = dict(id="call_abc", name="my_tool", arguments={"key": "val"})
        defaults.update(overrides)
        return ToolCallRequest(**defaults)

    def test_to_openai_tool_call_id(self):
        result = self._make().to_openai_tool_call()
        assert result["id"] == "call_abc"

    def test_to_openai_tool_call_type_is_function(self):
        assert self._make().to_openai_tool_call()["type"] == "function"

    def test_to_openai_tool_call_function_name(self):
        assert self._make().to_openai_tool_call()["function"]["name"] == "my_tool"

    def test_to_openai_tool_call_arguments_is_json_string(self):
        import json
        raw = self._make().to_openai_tool_call()["function"]["arguments"]
        parsed = json.loads(raw)
        assert parsed == {"key": "val"}

    def test_provider_specific_fields_included_when_set(self):
        tc = self._make(provider_specific_fields={"extra": "data"})
        result = tc.to_openai_tool_call()
        assert result["provider_specific_fields"] == {"extra": "data"}

    def test_provider_specific_fields_absent_when_none(self):
        result = self._make().to_openai_tool_call()
        assert "provider_specific_fields" not in result

    def test_function_provider_specific_fields_included_when_set(self):
        tc = self._make(function_provider_specific_fields={"fn_extra": 1})
        result = tc.to_openai_tool_call()
        assert result["function"]["provider_specific_fields"] == {"fn_extra": 1}

    def test_function_provider_specific_fields_absent_when_none(self):
        result = self._make().to_openai_tool_call()
        assert "provider_specific_fields" not in result["function"]


# ---------------------------------------------------------------------------
# LLMProvider._sanitize_empty_content (static)
# ---------------------------------------------------------------------------

class TestSanitizeEmptyContent:
    sanitize = staticmethod(LLMProvider._sanitize_empty_content)

    def test_non_empty_string_content_unchanged(self):
        msgs = [{"role": "user", "content": "hello"}]
        assert self.sanitize(msgs)[0]["content"] == "hello"

    def test_empty_string_user_content_becomes_placeholder(self):
        msgs = [{"role": "user", "content": ""}]
        assert self.sanitize(msgs)[0]["content"] == "(empty)"

    def test_empty_string_assistant_with_tool_calls_becomes_none(self):
        msgs = [{"role": "assistant", "content": "", "tool_calls": [{"id": "1"}]}]
        assert self.sanitize(msgs)[0]["content"] is None

    def test_empty_string_assistant_without_tool_calls_becomes_placeholder(self):
        msgs = [{"role": "assistant", "content": ""}]
        assert self.sanitize(msgs)[0]["content"] == "(empty)"

    def test_list_content_empty_text_block_is_removed(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": ""}]}]
        result = self.sanitize(msgs)[0]["content"]
        # All blocks removed → becomes placeholder
        assert result == "(empty)"

    def test_list_content_non_empty_text_block_preserved(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
        result = self.sanitize(msgs)[0]["content"]
        assert isinstance(result, list)
        assert result[0]["text"] == "hi"

    def test_list_content_meta_field_stripped(self):
        msgs = [
            {"role": "user", "content": [{"type": "text", "text": "hello", "_meta": "m"}]}
        ]
        result = self.sanitize(msgs)[0]["content"]
        assert isinstance(result, list)
        assert "_meta" not in result[0]
        assert result[0]["text"] == "hello"

    def test_dict_content_wrapped_in_list(self):
        msgs = [{"role": "user", "content": {"type": "text", "text": "hi"}}]
        result = self.sanitize(msgs)[0]["content"]
        assert isinstance(result, list)
        assert result[0] == {"type": "text", "text": "hi"}

    def test_multiple_messages_all_sanitized(self):
        msgs = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "ok"},
        ]
        result = self.sanitize(msgs)
        assert result[0]["content"] == "(empty)"
        assert result[1]["content"] == "ok"


# ---------------------------------------------------------------------------
# LLMProvider._sanitize_request_messages (static)
# ---------------------------------------------------------------------------

class TestSanitizeRequestMessages:
    sanitize = staticmethod(LLMProvider._sanitize_request_messages)
    _ALLOWED = frozenset({"role", "content", "tool_calls", "tool_call_id", "name"})

    def test_removes_disallowed_keys(self):
        msgs = [{"role": "user", "content": "hi", "secret_field": "x"}]
        result = self.sanitize(msgs, self._ALLOWED)
        assert "secret_field" not in result[0]
        assert result[0]["role"] == "user"

    def test_keeps_all_allowed_keys(self):
        msgs = [{"role": "user", "content": "hi", "name": "alice"}]
        result = self.sanitize(msgs, self._ALLOWED)
        assert result[0] == {"role": "user", "content": "hi", "name": "alice"}

    def test_assistant_without_content_gets_content_none(self):
        msgs = [{"role": "assistant", "tool_calls": []}]
        result = self.sanitize(msgs, self._ALLOWED)
        assert result[0]["content"] is None

    def test_non_assistant_without_content_not_injected(self):
        msgs = [{"role": "user"}]
        result = self.sanitize(msgs, self._ALLOWED)
        assert "content" not in result[0]

    def test_empty_messages_returns_empty_list(self):
        assert self.sanitize([], self._ALLOWED) == []

    def test_multiple_messages_all_sanitized(self):
        msgs = [
            {"role": "user", "content": "hi", "extra": "drop"},
            {"role": "assistant", "extra": "drop"},
        ]
        result = self.sanitize(msgs, self._ALLOWED)
        assert "extra" not in result[0]
        assert "extra" not in result[1]
        assert result[1]["content"] is None


# ---------------------------------------------------------------------------
# GenerationSettings
# ---------------------------------------------------------------------------

class TestGenerationSettings:
    def test_default_temperature(self):
        assert GenerationSettings().temperature == 0.7

    def test_default_max_tokens(self):
        assert GenerationSettings().max_tokens == 4096

    def test_default_reasoning_effort_is_none(self):
        assert GenerationSettings().reasoning_effort is None

    def test_custom_values(self):
        gs = GenerationSettings(temperature=0.2, max_tokens=512, reasoning_effort="high")
        assert gs.temperature == 0.2
        assert gs.max_tokens == 512
        assert gs.reasoning_effort == "high"

    def test_is_immutable(self):
        gs = GenerationSettings()
        with pytest.raises(Exception):
            gs.temperature = 1.0  # type: ignore[misc]
