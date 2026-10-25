from collections.abc import Awaitable, Callable

from .llm import AgentLLM
from .policy.tool_policy import ToolPolicy
from .tool_schema_validator import ToolSchemaValidator
from .models import ToolCall, ToolDefinition, ToolResult

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
            schema_validator: ToolSchemaValidator,
            tool_definitions: list[ToolDefinition],
            max_steps: int = 5,
    ):
        self._llm = llm
        self._tool_executor = tool_executor
        self._policy = policy
        self._schema_validator = schema_validator
        self._tool_definitions = tool_definitions
        self._max_steps = max_steps

    async def run(self, user_request: str) -> str:
        tool_results: list[ToolResult] = []

        for _ in range(self._max_steps):
            decision = await self._llm.decide(
                user_request=user_request,
                tool_definitions=self._tool_definitions,
                tool_results=tool_results,
            )

            if isinstance(decision, str):
                return decision

            self._policy.validate(
                decision.name,
                decision.arguments,
            )

            self._schema_validator.validate(decision)

            result = await self._tool_executor(decision)
            tool_results.append(result)

        raise RuntimeError(
            f"Agent exceeded maximum number of steps: {self._max_steps}"
        )
