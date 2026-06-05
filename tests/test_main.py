"""Tests for the main.py CLI entry point (secondary)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.main import (
    _build_llm_provider,
    _build_permission_policy,
    _build_provider_config,
    main,
)
from app.tools import AllowList, AlwaysAllow, AlwaysAsk, AskOnce


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCliArguments:
    def test_missing_p_flag_causes_system_exit(self):
        with patch("sys.argv", ["prog"]):
            with pytest.raises(SystemExit):
                main()

    def test_p_flag_is_required(self):
        with patch("sys.argv", ["prog", "--help"]):
            with pytest.raises(SystemExit):
                main()


# ---------------------------------------------------------------------------
# Provider config resolution
# ---------------------------------------------------------------------------

class TestProviderConfigResolution:
    def test_unknown_provider_raises_runtime_error(self):
        with pytest.raises(RuntimeError, match="Unknown provider"):
            _build_provider_config("missing-provider")

    def test_missing_api_key_raises_runtime_error(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            _build_provider_config("openrouter")

    def test_openrouter_defaults_base_url(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
        _spec, api_key, base_url = _build_provider_config("openrouter")
        assert api_key == "sk-test"
        assert base_url == "https://openrouter.ai/api/v1"


class TestProviderFactory:
    def test_openai_compat_backend_builds_openai_compat_provider(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        with patch("app.main.OpenAICompatProvider") as mock_provider:
            _build_llm_provider("openrouter", "openrouter/free")
        assert mock_provider.called

    def test_anthropic_backend_builds_anthropic_provider(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        with patch("app.main.AnthropicProvider") as mock_provider:
            _build_llm_provider("anthropic", "claude-sonnet-4-20250514")
        assert mock_provider.called


class TestPermissionPolicyFactory:
    def test_always_allow(self):
        assert isinstance(_build_permission_policy("always_allow"), AlwaysAllow)

    def test_always_ask(self):
        assert isinstance(_build_permission_policy("always_ask"), AlwaysAsk)

    def test_ask_once(self):
        assert isinstance(_build_permission_policy("ask_once"), AskOnce)

    def test_allow_list(self):
        policy = _build_permission_policy("allow_list", "read_file, write_file")
        assert isinstance(policy, AllowList)
        assert policy.names == {"read_file", "write_file"}

    def test_invalid_policy_raises(self):
        with pytest.raises(RuntimeError, match="Unknown permission policy"):
            _build_permission_policy("invalid")


# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------

class TestMainInvocation:
    def test_prompt_forwarded_to_agent_run(self, monkeypatch, capsys):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        with patch("sys.argv", ["prog", "-p", "say hello"]):
            with patch("app.main.AgentLoop") as mock_agent:
                mock_agent.return_value.run.return_value = "Hello!"
                with patch("app.main.OpenAICompatProvider"):
                    main()

        mock_agent.return_value.run.assert_called_once_with("say hello")
        assert "Hello!" in capsys.readouterr().out

    def test_model_arg_passed_to_agent(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        with patch("sys.argv", ["prog", "-p", "hi", "--model", "custom-model"]):
            with patch("app.main.AgentLoop") as mock_agent:
                mock_agent.return_value.run.return_value = ""
                with patch("app.main.OpenAICompatProvider"):
                    main()

        call_kwargs = mock_agent.call_args.kwargs
        assert call_kwargs.get("model") == "custom-model"

    def test_workspace_arg_passed_to_agent(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        with patch("sys.argv", ["prog", "-p", "hi", "--workspace", "/custom/workspace"]):
            with patch("app.main.AgentLoop") as mock_agent:
                mock_agent.return_value.run.return_value = ""
                with patch("app.main.OpenAICompatProvider"):
                    main()

        call_kwargs = mock_agent.call_args.kwargs
        assert call_kwargs.get("workspace") == Path("/custom/workspace")

    def test_provider_arg_affects_client_base_url_env_name(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://example.local/v1")
        with patch("sys.argv", ["prog", "-p", "hi", "--provider", "openai"]):
            with patch("app.main.AgentLoop") as mock_agent:
                mock_agent.return_value.run.return_value = "ok"
                with patch("app.main.OpenAICompatProvider") as mock_openai_compat:
                    main()

        mock_openai_compat.assert_called_once_with(
            api_key="sk-openai",
            base_url="https://example.local/v1",
            default_model="openrouter/free",
            spec=mock_openai_compat.call_args.kwargs["spec"],
        )


    def test_agent_result_printed_to_stdout(self, monkeypatch, capsys):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        with patch("sys.argv", ["prog", "-p", "q"]):
            with patch("app.main.AgentLoop") as mock_agent:
                mock_agent.return_value.run.return_value = "the answer"
                with patch("app.main.OpenAICompatProvider"):
                    main()

        assert "the answer" in capsys.readouterr().out
