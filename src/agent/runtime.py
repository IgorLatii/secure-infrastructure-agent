from collections.abc import Awaitable, Callable

from .llm import AgentLLM
from .models import ToolCall, ToolResult
from .policy.tool_policy import ToolPolicy


ToolExecutor = Callable[[ToolCall], Awaitable[ToolResult]]


class AgentRuntime:
    """
    Controls the agent execution loop.

    The LLM may propose tool calls, but only the runtime
    is allowed to execute them.
    """

    def __init__(
        self,
        llm: AgentLLM,
        tool_executor: ToolExecutor,
        policy: ToolPolicy,
        max_steps: int = 5,
    ):
        self._llm = llm
        self._tool_executor = tool_executor
        self._policy = policy
        self._max_steps = max_steps

    async def run(self, user_request: str) -> str:
        tool_results: list[ToolResult] = []

        for _ in range(self._max_steps):
            decision = self._llm.decide(
                user_request=user_request,
                tool_results=tool_results,
            )

            if isinstance(decision, str):
                return decision

            self._policy.validate(
                decision.name,
                decision.arguments,
            )

            result = await self._tool_executor(decision)
            tool_results.append(result)

        raise RuntimeError(
            f"Agent exceeded maximum number of steps: {self._max_steps}"
        )
