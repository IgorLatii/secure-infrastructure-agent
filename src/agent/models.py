from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """
    A tool invocation proposed by the LLM.

    The runtime must validate this request before execution.
    """

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """
    Result of a tool invocation returned to the agent runtime.
    """

    name: str
    content: dict[str, Any]