from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    """
    Provider-neutral description of a tool available to the LLM.

    Provider adapters translate this definition into their
    provider-specific tool/function calling format.
    """

    name: str
    description: str | None
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """
    A tool invocation proposed by the LLM.

    call_id correlates the invocation with its execution result
    without exposing provider-specific response objects to the runtime.
    """

    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    """
    Result of a tool invocation returned to the agent runtime.

    call_id identifies the ToolCall that produced this result.
    """

    call_id: str
    name: str
    content: dict[str, Any]