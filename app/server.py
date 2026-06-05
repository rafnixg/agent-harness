"""FastAPI server exposing AgentLoop over HTTP."""

import argparse
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agent import AgentLoop
from app.providers import build_llm_provider
from app.tools import build_permission_policy, build_tools


class AskRequest(BaseModel):
    """Request payload for agent question/answer endpoint."""

    prompt: str = Field(..., min_length=1)
    provider: str = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "openrouter")
    )
    model: str = Field(
        default_factory=lambda: os.getenv(
            "OPENROUTER_MODEL", os.getenv("LLM_MODEL", "openrouter/free")
        )
    )
    workspace: str = Field(
        default_factory=lambda: os.getenv("WORKSPACE_PATH", "./workspace")
    )
    permission_policy: str = Field(
        default_factory=lambda: os.getenv("PERMISSION_POLICY", "always_ask")
    )
    allow_tools: str = Field(
        default_factory=lambda: os.getenv("PERMISSION_ALLOWLIST", "")
    )


class AskResponse(BaseModel):
    """Response payload with final text returned by the agent."""

    result: str


app = FastAPI(title="Agent Harness API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    """Run one agent query and return the final answer."""
    try:
        provider = build_llm_provider(payload.provider, payload.model)
        permission_policy = build_permission_policy(
            payload.permission_policy,
            allowlist_raw=payload.allow_tools,
        )

        agent = AgentLoop(
            llm_provider=provider,
            model=payload.model,
            workspace=Path(payload.workspace),
        )
        agent.tools = build_tools(permission_policy=permission_policy)
        return AskResponse(result=agent.run(payload.prompt))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=500, detail="Internal server error") from e


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Run FastAPI app with uvicorn."""
    import uvicorn

    uvicorn.run("app.server:app", host=host, port=port, reload=reload)


def main() -> None:
    """CLI entry point for running the API server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("API_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "8000")))
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
