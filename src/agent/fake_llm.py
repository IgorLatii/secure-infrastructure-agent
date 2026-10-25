from .llm import AgentLLM
from .models import ToolCall, ToolDefinition, ToolResult


class FakeAgentLLM(AgentLLM):
    """
    Deterministic fake LLM used for testing the agent runtime.
    """

    def decide(
            self,
            user_request: str,
            tool_definitions: list[ToolDefinition],
            tool_results: list[ToolResult],
    ) -> ToolCall | str:
        if not tool_results:
            return ToolCall(
                call_id="fake-call-1",
                name="get_system_health",
                arguments={"target": "LAB-PC"},
            )

        return "System health evidence received."