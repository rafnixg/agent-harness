"""Main application file."""

import argparse
import os
from pathlib import Path

from app.agent import AgentLoop

from app.providers import build_llm_provider
from app.tools import build_permission_policy, build_tools


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
        default=os.getenv(
            "OPENROUTER_MODEL", os.getenv("LLM_MODEL", "openrouter/free")
        ),
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

    provider = build_llm_provider(args.provider, args.model)
    permission_policy = build_permission_policy(
        args.permission_policy,
        allowlist_raw=args.allow_tools,
    )

    agent = AgentLoop(
        llm_provider=provider,
        model=args.model,
        workspace=Path(args.workspace),
    )
    agent.tools = build_tools(permission_policy=permission_policy)

    result = agent.run(args.p)
    print(result)


if __name__ == "__main__":
    main()
