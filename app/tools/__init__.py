"""Tools are a way for agents to interact with the world outside of their own code. 
They can be used to access APIs, run commands, read and write files, and more.
This module contains the base Tool class, as well as some default tools like Bash.
"""

from app.tools.base import ToolRegistry, Tool
from app.tools.permission_policy import *
from app.tools.bash import BashTerminalTool
from app.tools.read_file import ReadFileTool
from app.tools.write_file import WriteFileTool

def build_tools(
    permission_policy: PermissionPolicy | None = None,
) -> ToolRegistry:
    """Create a registry with all default tools."""
    registry = ToolRegistry(permission_policy=permission_policy)
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(BashTerminalTool())
    return registry


def build_permission_policy(
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
            item.strip() for item in (allowlist_raw or "").split(",") if item.strip()
        }
        return AllowList(names=names)

    raise RuntimeError(
        "Unknown permission policy. Use one of: always_ask, always_allow, ask_once, allow_list"
    )
