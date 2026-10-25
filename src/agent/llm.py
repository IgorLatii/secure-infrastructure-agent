from abc import ABC, abstractmethod

from .models import ToolCall, ToolDefinition, ToolResult


class AgentLLM(ABC):
    """
    Abstract LLM interface used by the agent runtime.
    """

    @abstractmethod
    async def decide(
        self,
        user_request: str,
        tool_definitions: list[ToolDefinition],
        tool_results: list[ToolResult],
    ) -> ToolCall | str:
        """
        Returns either:
        - ToolCall: proposed invocation of an available tool
        - str: final response to the user
        """
        raise NotImplementedError