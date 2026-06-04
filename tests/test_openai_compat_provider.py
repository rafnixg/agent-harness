"""Tests for OpenAICompatProvider (secondary)."""

import json
import os
import string
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import LLMResponse
from app.providers.openai_compat_provider import OpenAICompatProvider, _short_tool_id
from app.providers.registry import ProviderSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_response(content: str | None = "hello", tool_calls=None, finish_reason="stop"):
    """Build a minimal mock that mimics an OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    msg.reasoning_content = None

    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = finish_reason

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 5
    usage.total_tokens = 15

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


def _make_chunk(content: str | None = None, finish_reason: str | None = None):
    """Build a minimal mock streaming chunk."""
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = None

    choice = MagicMock()
    choice.delta = delta
    choice.finish_reason = finish_reason

    chunk = MagicMock()
    chunk.choices = [choice]
    chunk.usage = None
    return chunk


async def _async_gen(*items):
    """Async generator used as a streaming response mock."""
    for item in items:
        yield item


_GATEWAY_SPEC = ProviderSpec(
    name="test_gw",
    keywords=("testgw",),
    env_key="TEST_GW_API_KEY",
    display_name="Test Gateway",
    is_gateway=True,
    default_api_base="http://test-gateway",
)

_DIRECT_SPEC = ProviderSpec(
    name="test_direct",
    keywords=("testdirect",),
    env_key="TEST_DIRECT_API_KEY",
    display_name="Test Direct",
    is_gateway=False,
    default_api_base="http://test-direct",
)


@pytest.fixture
def provider():
    """OpenAICompatProvider with AsyncOpenAI mocked out."""
    with patch("app.providers.openai_compat_provider.AsyncOpenAI"):
        p = OpenAICompatProvider(
            api_key="sk-test",
            base_url="http://test",
            default_model="test-model",
        )
    p._client = MagicMock()
    p._client.chat.completions.create = AsyncMock()
    return p


# ---------------------------------------------------------------------------
# _short_tool_id (module-level function)
# ---------------------------------------------------------------------------

class TestShortToolId:
    def test_length_is_nine(self):
        assert len(_short_tool_id()) == 9

    def test_is_alphanumeric(self):
        allowed = set(string.ascii_letters + string.digits)
        assert all(c in allowed for c in _short_tool_id())

    def test_ids_are_probabilistically_unique(self):
        ids = {_short_tool_id() for _ in range(200)}
        # With 62^9 possible values, collisions in 200 draws are astronomically unlikely
        assert len(ids) == 200


# ---------------------------------------------------------------------------
# _normalize_tool_call_id (static method)
# ---------------------------------------------------------------------------

class TestNormalizeToolCallId:
    normalize = staticmethod(OpenAICompatProvider._normalize_tool_call_id)

    def test_non_string_returned_unchanged(self):
        assert self.normalize(42) == 42
        assert self.normalize(None) is None

    def test_nine_char_alnum_returned_unchanged(self):
        assert self.normalize("abc123XYZ") == "abc123XYZ"

    def test_long_id_is_hashed_to_nine_chars(self):
        result = self.normalize("a" * 50)
        assert len(result) == 9

    def test_normalization_is_deterministic(self):
        long_id = "call_01234567890"
        assert self.normalize(long_id) == self.normalize(long_id)

    def test_short_non_alnum_id_is_hashed(self):
        result = self.normalize("call-1")
        assert len(result) == 9
        # sha1 hex digest only contains 0-9 and a-f, all alnum
        assert result.isalnum()

    def test_different_ids_produce_different_hashes(self):
        assert self.normalize("id_one_xxxxxx") != self.normalize("id_two_xxxxxx")


# ---------------------------------------------------------------------------
# _sanitize_messages (instance method)
# ---------------------------------------------------------------------------

class TestSanitizeMessages:
    def test_extra_keys_are_stripped(self, provider):
        msgs = [{"role": "user", "content": "hi", "extra": "drop"}]
        result = provider._sanitize_messages(msgs)
        assert "extra" not in result[0]

    def test_allowed_keys_are_preserved(self, provider):
        msgs = [{"role": "user", "content": "hi", "name": "alice"}]
        result = provider._sanitize_messages(msgs)
        assert result[0]["name"] == "alice"

    def test_tool_call_id_in_tool_message_normalized(self, provider):
        long_id = "b" * 30
        msgs = [{"role": "tool", "tool_call_id": long_id, "content": "result"}]
        result = provider._sanitize_messages(msgs)
        assert len(result[0]["tool_call_id"]) == 9

    def test_tool_call_ids_within_assistant_message_normalized(self, provider):
        long_id = "c" * 40
        msgs = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": long_id,
                        "type": "function",
                        "function": {"name": "t", "arguments": "{}"},
                    }
                ],
            }
        ]
        result = provider._sanitize_messages(msgs)
        assert len(result[0]["tool_calls"][0]["id"]) == 9

    def test_id_mapping_is_consistent_across_messages(self, provider):
        """Same original ID normalizes to the same value in both assistant and tool messages."""
        long_id = "d" * 35
        msgs = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": long_id,
                        "type": "function",
                        "function": {"name": "t", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": long_id, "content": "result"},
        ]
        result = provider._sanitize_messages(msgs)
        norm_in_call = result[0]["tool_calls"][0]["id"]
        norm_in_tool = result[1]["tool_call_id"]
        assert norm_in_call == norm_in_tool


# ---------------------------------------------------------------------------
# async chat()
# ---------------------------------------------------------------------------

class TestAsyncChat:
    async def test_returns_llm_response_with_content(self, provider):
        provider._client.chat.completions.create.return_value = _make_raw_response(content="Hello!")
        result = await provider.chat(messages=[{"role": "user", "content": "hi"}])
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello!"

    async def test_empty_choices_returns_error_response(self, provider):
        bad = MagicMock()
        bad.choices = []
        bad.usage = None
        provider._client.chat.completions.create.return_value = bad
        result = await provider.chat(messages=[{"role": "user", "content": "hi"}])
        assert result.finish_reason == "error"

    async def test_exception_returns_error_response(self, provider):
        provider._client.chat.completions.create.side_effect = RuntimeError("API down")
        result = await provider.chat(messages=[{"role": "user", "content": "hi"}])
        assert result.finish_reason == "error"
        assert "API down" in (result.content or "")

    async def test_explicit_model_is_forwarded_to_client(self, provider):
        provider._client.chat.completions.create.return_value = _make_raw_response()
        await provider.chat(messages=[{"role": "user", "content": "hi"}], model="gpt-x")
        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-x"

    async def test_default_model_used_when_none_given(self, provider):
        provider._client.chat.completions.create.return_value = _make_raw_response()
        await provider.chat(messages=[{"role": "user", "content": "hi"}])
        call_kwargs = provider._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "test-model"

    async def test_usage_extracted_from_response(self, provider):
        provider._client.chat.completions.create.return_value = _make_raw_response()
        result = await provider.chat(messages=[{"role": "user", "content": "hi"}])
        assert result.usage["prompt_tokens"] == 10
        assert result.usage["completion_tokens"] == 5
        assert result.usage["total_tokens"] == 15

    async def test_response_with_tool_call_has_tool_calls(self, provider):
        tc = MagicMock()
        tc.function.name = "my_tool"
        tc.function.arguments = '{"x": 1}'
        raw = _make_raw_response(content=None, tool_calls=[tc], finish_reason="tool_calls")
        provider._client.chat.completions.create.return_value = raw
        result = await provider.chat(messages=[{"role": "user", "content": "hi"}])
        assert result.has_tool_calls
        assert result.tool_calls[0].name == "my_tool"
        assert result.tool_calls[0].arguments == {"x": 1}


# ---------------------------------------------------------------------------
# async chat_stream()
# ---------------------------------------------------------------------------

class TestAsyncChatStream:
    async def test_aggregates_content_from_chunks(self, provider):
        chunks = [
            _make_chunk("Hello"),
            _make_chunk(", "),
            _make_chunk("world", finish_reason="stop"),
        ]
        provider._client.chat.completions.create.return_value = _async_gen(*chunks)
        result = await provider.chat_stream(messages=[{"role": "user", "content": "hi"}])
        assert result.content == "Hello, world"

    async def test_on_content_delta_called_per_chunk(self, provider):
        chunks = [_make_chunk("A"), _make_chunk("B"), _make_chunk("C", finish_reason="stop")]
        provider._client.chat.completions.create.return_value = _async_gen(*chunks)

        received: list[str] = []

        async def on_delta(text: str) -> None:
            received.append(text)

        await provider.chat_stream(
            messages=[{"role": "user", "content": "hi"}],
            on_content_delta=on_delta,
        )
        assert received == ["A", "B", "C"]

    async def test_exception_returns_error_response(self, provider):
        provider._client.chat.completions.create.side_effect = RuntimeError("stream broken")
        result = await provider.chat_stream(messages=[{"role": "user", "content": "hi"}])
        assert result.finish_reason == "error"
        assert "stream broken" in (result.content or "")

    async def test_finish_reason_from_last_chunk_preserved(self, provider):
        chunks = [_make_chunk("ok", finish_reason="stop")]
        provider._client.chat.completions.create.return_value = _async_gen(*chunks)
        result = await provider.chat_stream(messages=[{"role": "user", "content": "hi"}])
        assert result.finish_reason == "stop"


# ---------------------------------------------------------------------------
# get_default_model
# ---------------------------------------------------------------------------

class TestGetDefaultModel:
    def test_returns_configured_default_model(self):
        with patch("app.providers.openai_compat_provider.AsyncOpenAI"):
            p = OpenAICompatProvider(
                api_key="k", base_url="http://x", default_model="my-model"
            )
        assert p.get_default_model() == "my-model"


# ---------------------------------------------------------------------------
# _setup_env
# ---------------------------------------------------------------------------

class TestSetupEnv:
    def test_gateway_spec_always_overwrites_env_key(self, monkeypatch):
        monkeypatch.delenv("TEST_GW_API_KEY", raising=False)
        with patch("app.providers.openai_compat_provider.AsyncOpenAI"):
            OpenAICompatProvider(
                api_key="sk-gateway",
                base_url="http://x",
                spec=_GATEWAY_SPEC,
            )
        assert os.environ.get("TEST_GW_API_KEY") == "sk-gateway"

    def test_non_gateway_spec_uses_setdefault(self, monkeypatch):
        monkeypatch.setenv("TEST_DIRECT_API_KEY", "existing-value")
        with patch("app.providers.openai_compat_provider.AsyncOpenAI"):
            OpenAICompatProvider(
                api_key="new-key",
                base_url="http://x",
                spec=_DIRECT_SPEC,
            )
        # setdefault: existing value should NOT be overwritten
        assert os.environ["TEST_DIRECT_API_KEY"] == "existing-value"

    def test_no_spec_does_not_touch_env(self, monkeypatch):
        monkeypatch.delenv("TEST_GW_API_KEY", raising=False)
        with patch("app.providers.openai_compat_provider.AsyncOpenAI"):
            OpenAICompatProvider(api_key="sk-test", base_url="http://x")
        assert os.environ.get("TEST_GW_API_KEY") is None
