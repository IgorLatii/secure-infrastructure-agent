import pytest

from src.agent.fake_llm import FakeAgentLLM
from src.agent.models import ToolCall, ToolDefinition, ToolResult
from src.agent.runtime import AgentRuntime

from mcp.client import Client
from src.agent.mcp_executor import MCPToolExecutor
from src.windows_mcp.server import create_server
from src.agent.policy.tool_policy import ToolPolicy

from src.agent.tool_registry import MCPToolRegistry
from src.agent.tool_schema_validator import ToolSchemaValidator

from src.agent.audit.memory import MemoryAuditSink

TEST_TOOL_DEFINITIONS = [
    ToolDefinition(
        name="get_system_health",
        description="Get a read-only system health snapshot.",
        input_schema={
            "type": "object",
            "properties": {
                "target": {"type": "string"},
            },
            "required": ["target"],
        },
    ),
    ToolDefinition(
        name="get_top_processes",
        description="Get top resource-consuming processes.",
        input_schema={
            "type": "object",
            "properties": {
                "target": {"type": "string"},
            },
            "required": ["target"],
        },
    ),
]


class AllowAllSchemaValidator:
    def validate(self, call: ToolCall) -> None:
        pass

@pytest.fixture
def audit_sink() -> MemoryAuditSink:
    return MemoryAuditSink()

@pytest.mark.anyio
async def test_agent_runtime_executes_tool_and_returns_final_response(audit_sink):
    executed_calls: list[ToolCall] = []

    async def fake_tool_executor(call: ToolCall) -> ToolResult:
        executed_calls.append(call)

        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content={
                "target": "LAB-PC",
                "cpu_percent": 13.0,
            },
        )

    runtime = AgentRuntime(
        llm=FakeAgentLLM(),
        tool_executor=fake_tool_executor,
        policy=ToolPolicy(
            allowed_tools={"get_system_health"},
            allowed_targets={"LAB-PC"},
        ),
        schema_validator=AllowAllSchemaValidator(),
        tool_definitions=TEST_TOOL_DEFINITIONS,
        audit_sink=audit_sink,
    )

    response = await runtime.run(
        "Почему LAB-PC тормозит?"
    )

    assert response == "System health evidence received."

    assert len(executed_calls) == 1
    assert executed_calls[0].name == "get_system_health"
    assert executed_calls[0].arguments == {
        "target": "LAB-PC",
    }

    assert len(audit_sink.events) == 6

    run_started = audit_sink.events[0]

    assert run_started.event_type == "run_started"
    assert run_started.run_id
    assert run_started.step is None
    assert run_started.data["user_request"] == (
        "Почему LAB-PC тормозит?"
    )
    tool_proposed = audit_sink.events[1]

    policy_allowed = audit_sink.events[2]

    schema_allowed = audit_sink.events[3]

    tool_completed = audit_sink.events[4]

    assert tool_completed.event_type == "tool_completed"
    assert tool_completed.run_id == run_started.run_id
    assert tool_completed.step == 1
    assert tool_completed.data["tool_name"] == "get_system_health"
    assert tool_completed.data["call_id"] == tool_proposed.data["call_id"]
    assert tool_completed.data["content"] == {
        "target": "LAB-PC",
        "cpu_percent": 13.0,
    }
    assert schema_allowed.event_type == "schema_allowed"
    assert schema_allowed.run_id == run_started.run_id
    assert schema_allowed.step == 1
    assert schema_allowed.data["tool_name"] == "get_system_health"
    assert schema_allowed.data["call_id"] == tool_proposed.data["call_id"]
    assert policy_allowed.event_type == "policy_allowed"
    assert policy_allowed.run_id == run_started.run_id
    assert policy_allowed.step == 1
    assert policy_allowed.data["tool_name"] == "get_system_health"
    assert policy_allowed.data["call_id"] == tool_proposed.data["call_id"]
    assert tool_proposed.event_type == "tool_proposed"
    assert tool_proposed.run_id == run_started.run_id
    assert tool_proposed.step == 1
    assert tool_proposed.data["tool_name"] == "get_system_health"
    assert tool_proposed.data["arguments"] == {
        "target": "LAB-PC",
    }
    assert tool_proposed.data["call_id"]


@pytest.mark.anyio
async def test_agent_runtime_audits_tool_execution_failure(audit_sink):
    async def failing_tool_executor(call: ToolCall) -> ToolResult:
        raise RuntimeError("WinRM connection failed")

    runtime = AgentRuntime(
        llm=FakeAgentLLM(),
        tool_executor=failing_tool_executor,
        policy=ToolPolicy(
            allowed_tools={"get_system_health"},
            allowed_targets={"LAB-PC"},
        ),
        schema_validator=AllowAllSchemaValidator(),
        tool_definitions=TEST_TOOL_DEFINITIONS,
        audit_sink=audit_sink,
    )

    with pytest.raises(
            RuntimeError,
            match="WinRM connection failed",
    ):
        await runtime.run(
            "Почему LAB-PC тормозит?"
        )

    assert len(audit_sink.events) == 5

    run_started = audit_sink.events[0]
    tool_proposed = audit_sink.events[1]
    policy_allowed = audit_sink.events[2]
    schema_allowed = audit_sink.events[3]
    tool_failed = audit_sink.events[4]

    assert run_started.event_type == "run_started"
    assert tool_proposed.event_type == "tool_proposed"
    assert policy_allowed.event_type == "policy_allowed"
    assert schema_allowed.event_type == "schema_allowed"

    assert tool_failed.event_type == "tool_failed"
    assert tool_failed.run_id == run_started.run_id
    assert tool_failed.step == 1
    assert tool_failed.data["tool_name"] == "get_system_health"
    assert tool_failed.data["call_id"] == tool_proposed.data["call_id"]
    assert tool_failed.data["error_type"] == "RuntimeError"
    assert tool_failed.data["error"] == "WinRM connection failed"


@pytest.mark.anyio
async def test_agent_runtime_stops_after_max_steps(audit_sink):
    class EndlessToolLLM(FakeAgentLLM):
        async def decide(
                self,
                user_request: str,
                tool_definitions,
                tool_results: list[ToolResult],
        ) -> ToolCall | str:
            return ToolCall(
                call_id="test-call-1",
                name="get_system_health",
                arguments={"target": "LAB-PC"},
            )

    executed_calls: list[ToolCall] = []

    async def fake_tool_executor(call: ToolCall) -> ToolResult:
        executed_calls.append(call)

        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content={"target": "LAB-PC"},
        )

    runtime = AgentRuntime(
        llm=EndlessToolLLM(),
        tool_executor=fake_tool_executor,
        max_steps=3,
        policy=ToolPolicy(
            allowed_tools={"get_system_health"},
            allowed_targets={"LAB-PC"},
        ),
        schema_validator=AllowAllSchemaValidator(),
        tool_definitions=TEST_TOOL_DEFINITIONS,
        audit_sink=audit_sink,
    )

    with pytest.raises(
            RuntimeError,
            match="Agent exceeded maximum number of steps: 3",
    ):
        await runtime.run("Почему LAB-PC тормозит?")

    assert len(executed_calls) == 3

    assert len(audit_sink.events) == 14

    run_started = audit_sink.events[0]
    max_steps_exceeded = audit_sink.events[-1]

    assert run_started.event_type == "run_started"

    assert max_steps_exceeded.event_type == "max_steps_exceeded"
    assert max_steps_exceeded.run_id == run_started.run_id
    assert max_steps_exceeded.step == 3
    assert max_steps_exceeded.data["max_steps"] == 3
    tool_completed_events = [
        event
        for event in audit_sink.events
        if event.event_type == "tool_completed"
    ]

    assert len(tool_completed_events) == 3
    assert [event.step for event in tool_completed_events] == [1, 2, 3]

@pytest.mark.anyio
async def test_agent_runtime_executes_tool_through_mcp(audit_sink):
    mcp_server = create_server()

    async with Client(mcp_server) as client:
        mcp_executor = MCPToolExecutor(client)

        registry = MCPToolRegistry(client)
        await registry.load()

        schema_validator = ToolSchemaValidator(registry)

        tool_definitions = registry.get_tool_definitions()

        runtime = AgentRuntime(
            llm=FakeAgentLLM(),
            tool_executor=mcp_executor.execute,
            policy=ToolPolicy(
                allowed_tools={"get_system_health"},
                allowed_targets={"LAB-PC"},
            ),
            schema_validator=schema_validator,
            tool_definitions=tool_definitions,
            audit_sink=audit_sink,
        )

        response = await runtime.run(
            "Why is LAB-PC slow?"
        )

    assert response == "System health evidence received."


@pytest.mark.anyio
async def test_agent_runtime_blocks_disallowed_tool_before_execution(audit_sink):
    class UnsafeToolLLM:
        async def decide(self, user_request, tool_definitions, tool_results):
            return ToolCall(
                call_id="test-call-1",
                name="run_powershell",
                arguments={
                    "target": "LAB-PC",
                    "script": "Get-Process",
                },
            )

    executed_calls = []

    async def fake_tool_executor(call):
        executed_calls.append(call)

        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content={},
        )

    runtime = AgentRuntime(
        llm=UnsafeToolLLM(),
        tool_executor=fake_tool_executor,
        policy=ToolPolicy(
            allowed_tools={"get_system_health"},
            allowed_targets={"LAB-PC"},
        ),
        schema_validator=AllowAllSchemaValidator(),
        tool_definitions=TEST_TOOL_DEFINITIONS,
        audit_sink=audit_sink,
    )

    with pytest.raises(
            PermissionError,
            match="Tool is not allowed by policy: run_powershell",
    ):
        await runtime.run(
            "Run PowerShell on LAB-PC"
        )

    assert executed_calls == []
    assert len(audit_sink.events) == 3

    run_started = audit_sink.events[0]
    tool_proposed = audit_sink.events[1]
    policy_denied = audit_sink.events[2]

    assert run_started.event_type == "run_started"

    assert tool_proposed.event_type == "tool_proposed"
    assert tool_proposed.run_id == run_started.run_id
    assert tool_proposed.step == 1
    assert tool_proposed.data["tool_name"] == "run_powershell"

    assert policy_denied.event_type == "policy_denied"
    assert policy_denied.run_id == run_started.run_id
    assert policy_denied.step == 1
    assert policy_denied.data["tool_name"] == "run_powershell"
    assert policy_denied.data["call_id"] == tool_proposed.data["call_id"]
    assert policy_denied.data["reason"] == (
        "Tool is not allowed by policy: run_powershell"
    )


@pytest.mark.anyio
async def test_agent_runtime_blocks_disallowed_target_before_execution(audit_sink):
    class DisallowedTargetLLM:
        async def decide(self, user_request, tool_definitions, tool_results):
            return ToolCall(
                call_id="test-call-1",
                name="get_system_health",
                arguments={"target": "DC01"},
            )

    executed_calls = []

    async def fake_tool_executor(call):
        executed_calls.append(call)

        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content={},
        )

    runtime = AgentRuntime(
        llm=DisallowedTargetLLM(),
        tool_executor=fake_tool_executor,
        policy=ToolPolicy(
            allowed_tools={"get_system_health"},
            allowed_targets={"LAB-PC"},
        ),
        schema_validator=AllowAllSchemaValidator(),
        tool_definitions=TEST_TOOL_DEFINITIONS,
        audit_sink=audit_sink,
    )

    with pytest.raises(
            PermissionError,
            match="Target is not allowed by policy: DC01",
    ):
        await runtime.run(
            "Check system health on DC01"
        )

    assert executed_calls == []
    assert len(audit_sink.events) == 3

    run_started = audit_sink.events[0]
    tool_proposed = audit_sink.events[1]
    policy_denied = audit_sink.events[2]

    assert run_started.event_type == "run_started"

    assert tool_proposed.event_type == "tool_proposed"
    assert tool_proposed.run_id == run_started.run_id
    assert tool_proposed.step == 1
    assert tool_proposed.data["tool_name"] == "get_system_health"
    assert tool_proposed.data["arguments"] == {
        "target": "DC01",
    }

    assert policy_denied.event_type == "policy_denied"
    assert policy_denied.run_id == run_started.run_id
    assert policy_denied.step == 1
    assert policy_denied.data["tool_name"] == "get_system_health"
    assert policy_denied.data["call_id"] == tool_proposed.data["call_id"]
    assert policy_denied.data["reason"] == (
        "Target is not allowed by policy: DC01"
    )


@pytest.mark.anyio
async def test_agent_runtime_blocks_unexpected_argument_before_execution(audit_sink):
    class UnexpectedArgumentLLM:
        async def decide(self, user_request, tool_definitions, tool_results):
            return ToolCall(
                call_id="test-call-1",
                name="get_system_health",
                arguments={
                    "target": "LAB-PC",
                    "script": "Get-Process",
                },
            )

    executed_calls = []

    async def fake_tool_executor(call):
        executed_calls.append(call)

        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content={},
        )

    mcp_server = create_server()

    async with Client(mcp_server) as client:
        registry = MCPToolRegistry(client)
        await registry.load()

        schema_validator = ToolSchemaValidator(registry)

        runtime = AgentRuntime(
            llm=UnexpectedArgumentLLM(),
            tool_executor=fake_tool_executor,
            policy=ToolPolicy(
                allowed_tools={"get_system_health"},
                allowed_targets={"LAB-PC"},
            ),
            schema_validator=schema_validator,
            tool_definitions=TEST_TOOL_DEFINITIONS,
            audit_sink=audit_sink,
        )

        with pytest.raises(
                ValueError,
                match="Unexpected arguments",
        ):
            await runtime.run(
                "Check LAB-PC and execute this extra script"
            )

    assert executed_calls == []
    assert len(audit_sink.events) == 4

    run_started = audit_sink.events[0]
    tool_proposed = audit_sink.events[1]
    policy_allowed = audit_sink.events[2]
    schema_denied = audit_sink.events[3]

    assert run_started.event_type == "run_started"

    assert tool_proposed.event_type == "tool_proposed"
    assert tool_proposed.run_id == run_started.run_id
    assert tool_proposed.step == 1
    assert tool_proposed.data["tool_name"] == "get_system_health"
    assert tool_proposed.data["arguments"] == {
        "target": "LAB-PC",
        "script": "Get-Process",
    }

    assert policy_allowed.event_type == "policy_allowed"
    assert policy_allowed.run_id == run_started.run_id
    assert policy_allowed.step == 1
    assert policy_allowed.data["call_id"] == tool_proposed.data["call_id"]

    assert schema_denied.event_type == "schema_denied"
    assert schema_denied.run_id == run_started.run_id
    assert schema_denied.step == 1
    assert schema_denied.data["tool_name"] == "get_system_health"
    assert schema_denied.data["call_id"] == tool_proposed.data["call_id"]
    assert "Unexpected arguments" in schema_denied.data["reason"]


@pytest.mark.anyio
async def test_agent_runtime_passes_tool_definitions_to_llm(audit_sink):
    received_definitions = []

    class InspectingLLM:
        async def decide(
                self,
                user_request,
                tool_definitions,
                tool_results,
        ):
            received_definitions.extend(tool_definitions)
            return "Done."

    async def fake_tool_executor(call):
        raise AssertionError("Tool executor should not be called")

    runtime = AgentRuntime(
        llm=InspectingLLM(),
        tool_executor=fake_tool_executor,
        policy=ToolPolicy(
            allowed_tools={"get_system_health"},
            allowed_targets={"LAB-PC"},
        ),
        schema_validator=AllowAllSchemaValidator(),
        tool_definitions=TEST_TOOL_DEFINITIONS,
        audit_sink=audit_sink,
    )

    result = await runtime.run("Check LAB-PC")

    assert result == "Done."
    assert received_definitions == TEST_TOOL_DEFINITIONS


@pytest.mark.anyio
async def test_agent_runtime_performs_multi_step_diagnosis(audit_sink):
    class MultiStepDiagnosticLLM:
        async def decide(
                self,
                user_request,
                tool_definitions,
                tool_results,
        ):
            if not tool_results:
                return ToolCall(
                    call_id="health-call",
                    name="get_system_health",
                    arguments={"target": "LAB-PC"},
                )

            if len(tool_results) == 1:
                assert tool_results[0].name == "get_system_health"

                return ToolCall(
                    call_id="process-call",
                    name="get_top_processes",
                    arguments={"target": "LAB-PC"},
                )

            assert tool_results[1].name == "get_top_processes"

            return "High CPU and memory usage are associated with chrome.exe."

    executed_calls: list[ToolCall] = []

    async def fake_tool_executor(call: ToolCall) -> ToolResult:
        executed_calls.append(call)

        if call.name == "get_system_health":
            return ToolResult(
                call_id=call.call_id,
                name=call.name,
                content={
                    "target": "LAB-PC",
                    "cpu_percent": 87.0,
                    "memory": {
                        "used_percent": 88.75,
                    },
                },
            )

        if call.name == "get_top_processes":
            return ToolResult(
                call_id=call.call_id,
                name=call.name,
                content={
                    "target": "LAB-PC",
                    "top_by_cpu": [
                        {
                            "name": "chrome.exe",
                            "pid": 4120,
                            "cpu_percent": 42.0,
                            "memory_mb": 3200.0,
                        }
                    ],
                    "top_by_memory": [
                        {
                            "name": "chrome.exe",
                            "pid": 4120,
                            "cpu_percent": 42.0,
                            "memory_mb": 3200.0,
                        }
                    ],
                },
            )

        raise AssertionError(
            f"Unexpected tool call: {call.name}"
        )

    runtime = AgentRuntime(
        llm=MultiStepDiagnosticLLM(),
        tool_executor=fake_tool_executor,
        policy=ToolPolicy(
            allowed_tools={
                "get_system_health",
                "get_top_processes",
            },
            allowed_targets={"LAB-PC"},
        ),
        schema_validator=AllowAllSchemaValidator(),
        tool_definitions=TEST_TOOL_DEFINITIONS,
        audit_sink=audit_sink,
    )

    response = await runtime.run(
        "Почему LAB-PC тормозит?"
    )

    assert response == (
        "High CPU and memory usage are associated with chrome.exe."
    )

    assert [call.name for call in executed_calls] == [
        "get_system_health",
        "get_top_processes",
    ]


@pytest.mark.anyio
async def test_agent_runtime_performs_multi_step_diagnosis_through_mcp(audit_sink):
    class MultiStepDiagnosticLLM:
        async def decide(
                self,
                user_request,
                tool_definitions,
                tool_results,
        ):
            if not tool_results:
                return ToolCall(
                    call_id="health-call",
                    name="get_system_health",
                    arguments={"target": "LAB-PC"},
                )

            if len(tool_results) == 1:
                assert tool_results[0].name == "get_system_health"
                assert tool_results[0].content["cpu_percent"] == 87.0

                return ToolCall(
                    call_id="process-call",
                    name="get_top_processes",
                    arguments={"target": "LAB-PC"},
                )

            assert tool_results[1].name == "get_top_processes"
            assert (
                    tool_results[1].content["top_by_cpu"][0]["name"]
                    == "chrome.exe"
            )

            return "Multi-step diagnosis complete."

    mcp_server = create_server()

    async with Client(mcp_server) as client:
        mcp_executor = MCPToolExecutor(client)

        registry = MCPToolRegistry(client)
        await registry.load()

        runtime = AgentRuntime(
            llm=MultiStepDiagnosticLLM(),
            tool_executor=mcp_executor.execute,
            policy=ToolPolicy(
                allowed_tools={
                    "get_system_health",
                    "get_top_processes",
                },
                allowed_targets={"LAB-PC"},
            ),
            schema_validator=ToolSchemaValidator(registry),
            tool_definitions=registry.get_tool_definitions(),
            audit_sink=audit_sink,
        )

        response = await runtime.run(
            "Почему LAB-PC тормозит?"
        )

    assert response == "Multi-step diagnosis complete."
