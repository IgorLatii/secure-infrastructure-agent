from collections.abc import Awaitable, Callable

from .llm import AgentLLM
from .policy.tool_policy import ToolPolicy
from .tool_schema_validator import ToolSchemaValidator
from .models import ToolCall, ToolDefinition, ToolResult
from .audit.sink import AuditSink

from uuid import uuid4

from .audit.models import AuditEvent


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
            audit_sink: AuditSink,
            max_steps: int = 5,
    ):
        self._llm = llm
        self._tool_executor = tool_executor
        self._policy = policy
        self._schema_validator = schema_validator
        self._tool_definitions = tool_definitions
        self._audit_sink = audit_sink
        self._max_steps = max_steps

    async def run(self, user_request: str) -> str:
        run_id = str(uuid4())

        self._audit_sink.write(
            AuditEvent(
                event_type="run_started",
                run_id=run_id,
                data={
                    "user_request": user_request,
                },
            )
        )

        tool_results: list[ToolResult] = []

        for step in range(1, self._max_steps + 1):
            decision = await self._llm.decide(
                user_request=user_request,
                tool_definitions=self._tool_definitions,
                tool_results=tool_results,
            )

            if isinstance(decision, str):
                self._audit_sink.write(
                    AuditEvent(
                        event_type="final_answer",
                        run_id=run_id,
                        step=step,
                        data={
                            "answer": decision,
                        },
                    )
                )

                return decision

            self._audit_sink.write(
                AuditEvent(
                    event_type="tool_proposed",
                    run_id=run_id,
                    step=step,
                    data={
                        "call_id": decision.call_id,
                        "tool_name": decision.name,
                        "arguments": decision.arguments,
                    },
                )
            )

            try:
                self._policy.validate(
                    decision.name,
                    decision.arguments,
                )
            except PermissionError as exc:
                self._audit_sink.write(
                    AuditEvent(
                        event_type="policy_denied",
                        run_id=run_id,
                        step=step,
                        data={
                            "call_id": decision.call_id,
                            "tool_name": decision.name,
                            "reason": str(exc),
                        },
                    )
                )
                raise

            self._audit_sink.write(
                AuditEvent(
                    event_type="policy_allowed",
                    run_id=run_id,
                    step=step,
                    data={
                        "call_id": decision.call_id,
                        "tool_name": decision.name,
                    },
                )
            )

            try:
                self._schema_validator.validate(decision)
            except ValueError as exc:
                self._audit_sink.write(
                    AuditEvent(
                        event_type="schema_denied",
                        run_id=run_id,
                        step=step,
                        data={
                            "call_id": decision.call_id,
                            "tool_name": decision.name,
                            "reason": str(exc),
                        },
                    )
                )
                raise

            self._audit_sink.write(
                AuditEvent(
                    event_type="schema_allowed",
                    run_id=run_id,
                    step=step,
                    data={
                        "call_id": decision.call_id,
                        "tool_name": decision.name,
                    },
                )
            )

            try:
                result = await self._tool_executor(decision)
            except Exception as exc:
                self._audit_sink.write(
                    AuditEvent(
                        event_type="tool_failed",
                        run_id=run_id,
                        step=step,
                        data={
                            "call_id": decision.call_id,
                            "tool_name": decision.name,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                )
                raise

            self._audit_sink.write(
                AuditEvent(
                    event_type="tool_completed",
                    run_id=run_id,
                    step=step,
                    data={
                        "call_id": result.call_id,
                        "tool_name": result.name,
                        "content": result.content,
                    },
                )
            )

            tool_results.append(result)

        self._audit_sink.write(
            AuditEvent(
                event_type="max_steps_exceeded",
                run_id=run_id,
                step=self._max_steps,
                data={
                    "max_steps": self._max_steps,
                },
            )
        )

        raise RuntimeError(
            f"Agent exceeded maximum number of steps: {self._max_steps}"
        )
