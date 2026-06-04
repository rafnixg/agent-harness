"""Tests for providers/base.py data classes and static helpers (secondary)."""

from collections import deque
from typing import Any
from unittest.mock import AsyncMock, patch

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


# ---------------------------------------------------------------------------
# LLMProvider._is_transient_error
# ---------------------------------------------------------------------------

class TestIsTransientError:
    @pytest.mark.parametrize("marker", LLMProvider._TRANSIENT_ERROR_MARKERS)
    def test_each_marker_detected(self, marker):
        assert LLMProvider._is_transient_error(f"Error: {marker} happened") is True

    def test_non_transient_returns_false(self):
        assert LLMProvider._is_transient_error("Invalid request body") is False

    def test_none_returns_false(self):
        assert LLMProvider._is_transient_error(None) is False

    def test_empty_string_returns_false(self):
        assert LLMProvider._is_transient_error("") is False

    def test_detection_is_case_insensitive(self):
        assert LLMProvider._is_transient_error("Error: RATE LIMIT exceeded") is True
        assert LLMProvider._is_transient_error("Error: Overloaded") is True


# ---------------------------------------------------------------------------
# LLMProvider._strip_image_content
# ---------------------------------------------------------------------------

class TestStripImageContent:
    def test_returns_none_when_no_images_present(self):
        msgs = [{"role": "user", "content": "hello"}]
        assert LLMProvider._strip_image_content(msgs) is None

    def test_replaces_image_url_block_with_text_placeholder(self):
        msgs = [{"role": "user", "content": [{"type": "image_url"}]}]
        result = LLMProvider._strip_image_content(msgs)
        assert result is not None
        block = result[0]["content"][0]
        assert block["type"] == "text"
        assert "image" in block["text"]

    def test_path_in_meta_appears_in_placeholder(self):
        msgs = [
            {"role": "user", "content": [{"type": "image_url", "_meta": {"path": "photo.png"}}]}
        ]
        result = LLMProvider._strip_image_content(msgs)
        assert result is not None
        assert "photo.png" in result[0]["content"][0]["text"]

    def test_preserves_non_image_blocks_before_and_after(self):
        msgs = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "describe this"},
                    {"type": "image_url"},
                    {"type": "text", "text": "please"},
                ],
            }
        ]
        result = LLMProvider._strip_image_content(msgs)
        assert result is not None
        content = result[0]["content"]
        assert content[0]["text"] == "describe this"
        assert content[1]["type"] == "text"  # replaced image
        assert content[2]["text"] == "please"

    def test_string_content_messages_are_passed_through(self):
        msgs = [
            {"role": "user", "content": "no images here"},
            {"role": "user", "content": [{"type": "image_url"}]},
        ]
        result = LLMProvider._strip_image_content(msgs)
        assert result is not None
        assert result[0]["content"] == "no images here"

    def test_multiple_images_all_replaced(self):
        msgs = [
            {"role": "user", "content": [{"type": "image_url"}, {"type": "image_url"}]}
        ]
        result = LLMProvider._strip_image_content(msgs)
        assert result is not None
        assert all(b["type"] == "text" for b in result[0]["content"])


# ---------------------------------------------------------------------------
# LLMProvider.chat_with_retry  (async)
# ---------------------------------------------------------------------------

class _ConcreteProvider(LLMProvider):
    """Minimal concrete LLMProvider for testing retry logic."""

    def __init__(self):
        super().__init__(api_key="test", base_url="http://test")
        self._queue: deque[LLMResponse] = deque()

    def push(self, response: LLMResponse) -> None:
        self._queue.append(response)

    async def chat(
        self,
        messages,
        tools=None,
        model=None,
        max_tokens=4096,
        temperature=0.7,
        reasoning_effort=None,
        tool_choice=None,
    ) -> LLMResponse:
        if self._queue:
            return self._queue.popleft()
        return LLMResponse(content="default")

    def get_default_model(self) -> str:
        return "test-model"


class TestChatWithRetry:
    def setup_method(self):
        self.provider = _ConcreteProvider()

    async def test_success_on_first_attempt_returns_immediately(self):
        self.provider.push(LLMResponse(content="ok"))
        result = await self.provider.chat_with_retry(
            messages=[{"role": "user", "content": "hi"}]
        )
        assert result.content == "ok"
        assert result.finish_reason == "stop"

    async def test_non_transient_error_returned_without_retry(self):
        """A permanent error (not in _TRANSIENT_ERROR_MARKERS) stops immediately."""
        self.provider.push(LLMResponse(content="Invalid API key", finish_reason="error"))
        self.provider.push(LLMResponse(content="should not reach"))

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await self.provider.chat_with_retry(
                messages=[{"role": "user", "content": "hi"}]
            )

        assert result.content == "Invalid API key"
        mock_sleep.assert_not_called()

    async def test_transient_error_triggers_retries(self):
        """A 429 causes 3 sleeps and a final successful call."""
        transient = LLMResponse(content="Error: 429 rate limit", finish_reason="error")
        success = LLMResponse(content="success after retries")
        for _ in range(3):  # consumed in the for-loop
            self.provider.push(transient)
        self.provider.push(success)  # consumed by the final call after loop

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await self.provider.chat_with_retry(
                messages=[{"role": "user", "content": "hi"}]
            )

        assert result.content == "success after retries"
        assert mock_sleep.call_count == 3

    async def test_retry_delay_sequence_is_1_2_4(self):
        """Exponential back-off delays match _CHAT_RETRY_DELAYS = (1, 2, 4)."""
        transient = LLMResponse(content="Error: 503", finish_reason="error")
        for _ in range(3):
            self.provider.push(transient)
        self.provider.push(LLMResponse(content="ok"))

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await self.provider.chat_with_retry(
                messages=[{"role": "user", "content": "hi"}]
            )

        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert delays == [1, 2, 4]

    async def test_all_retries_exhausted_returns_last_error_response(self):
        """When every attempt fails, the final error response is returned."""
        transient = LLMResponse(content="Error: 502 bad gateway", finish_reason="error")
        for _ in range(4):  # 3 in loop + 1 final
            self.provider.push(transient)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await self.provider.chat_with_retry(
                messages=[{"role": "user", "content": "hi"}]
            )

        assert result.finish_reason == "error"

