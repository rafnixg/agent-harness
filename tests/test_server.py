"""Tests for FastAPI server endpoints."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.server import app


class TestServerHealth:
    def test_health_returns_ok(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestServerAsk:
    def test_ask_returns_agent_result(self):
        client = TestClient(app)

        with patch("app.server.build_llm_provider") as mock_build_provider:
            with patch("app.server.build_permission_policy") as mock_policy:
                with patch("app.server.build_tools") as mock_build_tools:
                    with patch("app.server.AgentLoop") as mock_agent:
                        mock_build_provider.return_value = object()
                        mock_policy.return_value = object()
                        mock_build_tools.return_value = object()
                        mock_agent.return_value.run.return_value = "respuesta"

                        response = client.post(
                            "/ask",
                            json={
                                "prompt": "hola",
                                "provider": "openrouter",
                                "model": "openrouter/free",
                                "workspace": "./workspace",
                                "permission_policy": "always_allow",
                                "allow_tools": "read_file",
                            },
                        )

        assert response.status_code == 200
        assert response.json() == {"result": "respuesta"}
        mock_build_provider.assert_called_once_with("openrouter", "openrouter/free")
        mock_policy.assert_called_once_with("always_allow", allowlist_raw="read_file")
        mock_agent.assert_called_once_with(
            llm_provider=mock_build_provider.return_value,
            model="openrouter/free",
            workspace=Path("./workspace"),
        )

    def test_ask_maps_runtime_error_to_400(self):
        client = TestClient(app)

        with patch("app.server.build_llm_provider") as mock_build_provider:
            mock_build_provider.side_effect = RuntimeError("bad config")
            response = client.post(
                "/ask",
                json={
                    "prompt": "hola",
                    "provider": "openrouter",
                    "model": "openrouter/free",
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "bad config"
