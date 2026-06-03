"""Shared pytest fixtures, marks, and configuration."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agent import AgentLoop
from app.tool import ToolRegistry


# ---------------------------------------------------------------------------
# LLM response factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_response():
    """Factory that builds a minimal mock OpenAI chat completion response."""

    def _factory(content=None, tool_calls=None):
        message = MagicMock()
        message.content = content
        message.tool_calls = tool_calls or []

        choice = MagicMock()
        choice.message = message

        response = MagicMock()
        response.choices = [choice]
        return response

    return _factory


@pytest.fixture
def make_tool_call():
    """Factory that builds a minimal mock function tool-call object."""

    def _factory(name, arguments, call_id="call_1"):
        tc = MagicMock()
        tc.type = "function"
        tc.id = call_id
        tc.function.name = name
        tc.function.arguments = json.dumps(arguments)
        return tc

    return _factory


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry():
    """Empty ToolRegistry."""
    return ToolRegistry()


@pytest.fixture
def mock_provider():
    """MagicMock that mimics the OpenAI client used by AgentLoop."""
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"
    return provider


@pytest.fixture
def agent(mock_provider, tmp_path):
    """AgentLoop with a mock provider and a temporary workspace."""
    return AgentLoop(
        llm_provider=mock_provider,
        workspace=tmp_path,
        model="test-model",
    )


@pytest.fixture
def tmp_workspace(tmp_path):
    """Temporary workspace directory."""
    return tmp_path


# ---------------------------------------------------------------------------
# Custom marks + live-test skip logic
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: mark test as requiring a live LLM API key (OPENROUTER_API_KEY)",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an end-to-end integration test (mocked LLM)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.live tests unless RUN_LIVE_TESTS=1 is set."""
    if os.environ.get("RUN_LIVE_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="Set RUN_LIVE_TESTS=1 to run live API tests")
    for item in items:
        if item.get_closest_marker("live"):
            item.add_marker(skip)
