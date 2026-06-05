"""Permission policies for tool execution.
Defines how the agent should decide whether to execute a tool call,
potentially prompting the user for confirmation.
"""

from abc import ABC, abstractmethod
from typing import Any, Literal
from dataclasses import dataclass, field


PermissionDecision = Literal["allow", "deny", "ask"]


class PermissionPolicy(ABC):
    """Policy that decides whether a tool call should be executed."""

    @abstractmethod
    def decide(self, name: str, tool_input: dict[str, Any]) -> PermissionDecision:
        """Return `allow`, `deny`, or `ask` for a tool invocation."""


class AlwaysAllow(PermissionPolicy):
    """Never prompt and always allow tool execution."""

    def decide(self, name: str, tool_input: dict[str, Any]) -> PermissionDecision:
        return "allow"


class AlwaysAsk(PermissionPolicy):
    """Prompt for every tool execution."""

    def decide(self, name: str, tool_input: dict[str, Any]) -> PermissionDecision:
        return "ask"


@dataclass
class AllowList(PermissionPolicy):
    """Allow selected tool names and ask for everything else."""

    names: set[str] = field(default_factory=set)

    def decide(self, name: str, tool_input: dict[str, Any]) -> PermissionDecision:
        if name in self.names:
            return "allow"
        return "ask"


@dataclass
class AskOnce(PermissionPolicy):
    """Ask once per tool name, then remember allow/deny for this session."""

    _memory: dict[str, bool] = field(default_factory=dict)

    def decide(self, name: str, tool_input: dict[str, Any]) -> PermissionDecision:
        if name in self._memory:
            return "allow" if self._memory[name] else "deny"
        return "ask"

    def remember(self, name: str, allowed: bool) -> None:
        """Persist the user decision for future calls in this process."""
        self._memory[name] = allowed

__all__ = [
    "PermissionPolicy",
    "AlwaysAllow",
    "AlwaysAsk",
    "AllowList",
    "AskOnce"
]
