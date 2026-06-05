"""Base tool classes and registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


PermissionDecision = Literal["allow", "deny", "ask"]


class Tool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name used for function calls."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the LLM."""

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON schema for tool parameters."""

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        """Execute the tool with given arguments."""

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


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


class ToolRegistry:
    """Registry to manage and execute tools."""

    def __init__(self, permission_policy: PermissionPolicy | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._permission_policy = permission_policy or AlwaysAsk()

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """Get a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def confirm(self, name: str, kwargs: dict[str, Any]) -> bool:
        """Ask user for confirmation before executing a tool."""
        response = input(
            f"Agent wants to execute '{name}' with {kwargs}. Allow? (y/n): "
        ).strip().lower()
        return response == "y"

    def execute(self, name: str, **kwargs: Any) -> str:
        """Execute a tool by name with given arguments."""
        decision = self._permission_policy.decide(name, kwargs)
        if decision == "deny":
            return "Tool execution cancelled by user."

        if decision == "ask":
            allowed = self.confirm(name, kwargs)
            if isinstance(self._permission_policy, AskOnce):
                self._permission_policy.remember(name, allowed)
            if not allowed:
                return "Tool execution cancelled by user."

        return self.get(name).execute(**kwargs)

    def to_openai_schema(self) -> list[dict[str, Any]]:
        """Convert all registered tools to OpenAI format."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self._tools.values())
