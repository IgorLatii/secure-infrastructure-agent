from abc import ABC, abstractmethod

from .models import ToolCall, ToolResult


class AgentLLM(ABC):
    """
    Abstract LLM interface used by the agent runtime.
    """

    @abstractmethod
    def decide(
        self,
        user_request: str,
        tool_results: list[ToolResult],
    ) -> ToolCall | str:
        """
        Decide the next agent action.

        Returns either:
        - ToolCall: request execution of a tool
        - str: final response to the user
        """
        raise NotImplementedError