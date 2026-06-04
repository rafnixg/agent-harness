"""Main application file."""

import argparse
import os
from pathlib import Path

from app.agent import AgentLoop
from app.providers.antropic_provider import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.openai_compat_provider import OpenAICompatProvider
from app.providers.registry import ProviderSpec, find_by_name
from app.tools import create_default_registry


def _build_provider_config(
    provider_name: str,
) -> tuple[ProviderSpec, str | None, str | None]:
    """Resolve provider spec, API key and base URL using ProviderSpec metadata."""
    spec = find_by_name(provider_name)
    if spec is None:
        raise RuntimeError(f"Unknown provider: {provider_name}")

    api_key = os.getenv(spec.env_key) if spec.env_key else None
    base_env = f"{spec.name.upper()}_BASE_URL"
    base_url = os.getenv(base_env) or spec.default_base_url or None

    if spec.env_key and not api_key and not spec.is_oauth and not spec.is_direct:
        raise RuntimeError(f"{spec.env_key} is not set")

    return spec, api_key, base_url


def _build_llm_provider(provider_name: str, model: str) -> LLMProvider:
    """Create a concrete LLMProvider based on ProviderSpec backend."""
    spec, api_key, base_url = _build_provider_config(provider_name)

    if spec.backend == "openai_compat":
        return OpenAICompatProvider(
            api_key=api_key,
            base_url=base_url,
            default_model=model,
            spec=spec,
        )

    if spec.backend == "anthropic":
        return AnthropicProvider(
            api_key=api_key,
            api_base=base_url,
            default_model=model,
        )

    raise RuntimeError(f"Unsupported provider backend: {spec.backend}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", required=True, help="Prompt to send to the agent")
    parser.add_argument(
        "--provider",
        default=os.getenv("LLM_PROVIDER", "openrouter"),
        help="Provider name from registry (default: openrouter)",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENROUTER_MODEL", os.getenv("LLM_MODEL", "openrouter/free")),
        help="Model name to send to the provider",
    )
    parser.add_argument(
        "--workspace",
        default=os.getenv("WORKSPACE_PATH", "./workspace"),
        help="Workspace path for tool operations",
    )
    args = parser.parse_args()

    provider = _build_llm_provider(args.provider, args.model)

    agent = AgentLoop(
        llm_provider=provider,
        model=args.model,
        workspace=Path(args.workspace),
    )
    for tool in create_default_registry():
        agent.tools.register(tool)

    result = agent.run(args.p)
    print(result)


if __name__ == "__main__":
    main()
