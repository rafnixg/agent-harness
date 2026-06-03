"""Tests for the main.py CLI entry point (secondary)."""

from unittest.mock import MagicMock, patch

import pytest

import app.main as main_module
from app.main import main


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
# API key validation
# ---------------------------------------------------------------------------

class TestApiKeyValidation:
    def test_missing_api_key_raises_runtime_error(self, monkeypatch):
        monkeypatch.setattr(main_module, "API_KEY", None)
        with patch("sys.argv", ["prog", "-p", "hello"]):
            with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
                main()

    def test_present_api_key_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(main_module, "API_KEY", "sk-test")
        with patch("sys.argv", ["prog", "-p", "hello"]):
            with patch("app.main.OpenAI"):
                with patch("app.main.AgentLoop") as MockAgent:
                    MockAgent.return_value.run.return_value = ""
                    main()  # should not raise


# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------

class TestAgentInvocation:
    def test_prompt_forwarded_to_agent_run(self, monkeypatch, capsys):
        monkeypatch.setattr(main_module, "API_KEY", "sk-test")
        with patch("sys.argv", ["prog", "-p", "say hello"]):
            with patch("app.main.OpenAI"):
                with patch("app.main.AgentLoop") as MockAgent:
                    MockAgent.return_value.run.return_value = "Hello!"
                    main()

        MockAgent.return_value.run.assert_called_once_with("say hello")
        assert "Hello!" in capsys.readouterr().out

    def test_model_env_var_passed_to_agent(self, monkeypatch):
        monkeypatch.setattr(main_module, "API_KEY", "sk-test")
        monkeypatch.setattr(main_module, "MODEL", "custom-model")
        with patch("sys.argv", ["prog", "-p", "hi"]):
            with patch("app.main.OpenAI"):
                with patch("app.main.AgentLoop") as MockAgent:
                    MockAgent.return_value.run.return_value = ""
                    main()

        call_kwargs = MockAgent.call_args.kwargs
        assert call_kwargs.get("model") == "custom-model"

    def test_workspace_path_passed_to_agent(self, monkeypatch):
        from pathlib import Path

        monkeypatch.setattr(main_module, "API_KEY", "sk-test")
        monkeypatch.setattr(main_module, "WORKSPACE_PATH", "/custom/workspace")
        with patch("sys.argv", ["prog", "-p", "hi"]):
            with patch("app.main.OpenAI"):
                with patch("app.main.AgentLoop") as MockAgent:
                    MockAgent.return_value.run.return_value = ""
                    main()

        call_kwargs = MockAgent.call_args.kwargs
        assert call_kwargs.get("workspace") == Path("/custom/workspace")

    def test_agent_result_printed_to_stdout(self, monkeypatch, capsys):
        monkeypatch.setattr(main_module, "API_KEY", "sk-test")
        with patch("sys.argv", ["prog", "-p", "q"]):
            with patch("app.main.OpenAI"):
                with patch("app.main.AgentLoop") as MockAgent:
                    MockAgent.return_value.run.return_value = "the answer"
                    main()

        assert "the answer" in capsys.readouterr().out
