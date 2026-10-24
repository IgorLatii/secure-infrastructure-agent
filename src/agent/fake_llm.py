from .llm import AgentLLM
from .models import ToolCall, ToolResult


class FakeAgentLLM(AgentLLM):
    """
    Deterministic fake LLM used for testing the agent runtime.
    """

    def decide(
        self,
        user_request: str,
        tool_results: list[ToolResult],
    ) -> ToolCall | str:
        if not tool_results:
            return ToolCall(
                name="get_system_health",
                arguments={"target": "LAB-PC"},
            )

        return "System health evidence received."