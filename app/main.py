"""Main application file."""

import argparse
import os
from pathlib import Path

from app.agent import AgentLoop
from app.providers.antropic_provider import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.openai_compat_provider import OpenAICompatProvider
from app.providers.registry import ProviderSpec, find_by_name
from app.tools.permission_policy import AllowList, AlwaysAllow, AlwaysAsk, AskOnce, PermissionPolicy
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


def _build_permission_policy(
    policy_name: str,
    allowlist_raw: str | None = None,
) -> PermissionPolicy:
    """Build permission policy from cli/env value."""
    normalized = policy_name.strip().lower().replace("-", "_")

    if normalized == "always_allow":
        return AlwaysAllow()
    if normalized == "always_ask":
        return AlwaysAsk()
    if normalized == "ask_once":
        return AskOnce()
    if normalized == "allow_list":
        names = {
            item.strip()
            for item in (allowlist_raw or "").split(",")
            if item.strip()
        }
        return AllowList(names=names)

    raise RuntimeError(
        "Unknown permission policy. Use one of: always_ask, always_allow, ask_once, allow_list"
    )


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
    parser.add_argument(
        "--permission-policy",
        default=os.getenv("PERMISSION_POLICY", "always_ask"),
        help="Permission policy: always_ask, always_allow, ask_once, allow_list",
    )
    parser.add_argument(
        "--allow-tools",
        default=os.getenv("PERMISSION_ALLOWLIST", ""),
        help="Comma-separated tools allowed when --permission-policy=allow_list",
    )
    args = parser.parse_args()

    provider = _build_llm_provider(args.provider, args.model)
    permission_policy = _build_permission_policy(
        args.permission_policy,
        allowlist_raw=args.allow_tools,
    )

    agent = AgentLoop(
        llm_provider=provider,
        model=args.model,
        workspace=Path(args.workspace),
    )
    agent.tools = create_default_registry(permission_policy=permission_policy)

    result = agent.run(args.p)
    print(result)


if __name__ == "__main__":
    main()
