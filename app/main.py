"""Main application file."""

import argparse
import os
from pathlib import Path
from openai import OpenAI

from app.agent import AgentLoop
from app.tools import create_default_registry

# Configuration from environment variables
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
MODEL = os.getenv("OPENROUTER_MODEL", default="openrouter/free")
WORKSPACE_PATH = os.getenv("WORKSPACE_PATH", default="./workspace")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", required=True, help="Prompt to send to the agent")
    args = parser.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    agent = AgentLoop(
        llm_provider=client,
        model=MODEL,
        workspace=Path(WORKSPACE_PATH),
    )
    for tool in create_default_registry():
        agent.tools.register(tool)

    result = agent.run(args.p)
    print(result)


if __name__ == "__main__":
    main()
