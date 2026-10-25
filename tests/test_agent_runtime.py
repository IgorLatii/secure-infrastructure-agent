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
    )
]

class AllowAllSchemaValidator:
    def validate(self, call: ToolCall) -> None:
        pass


@pytest.mark.anyio
async def test_agent_runtime_executes_tool_and_returns_final_response():
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

@pytest.mark.anyio
async def test_agent_runtime_stops_after_max_steps():
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
    )

    with pytest.raises(
        RuntimeError,
        match="Agent exceeded maximum number of steps: 3",
    ):
        await runtime.run("Почему LAB-PC тормозит?")

    assert len(executed_calls) == 3


@pytest.mark.anyio
async def test_agent_runtime_executes_tool_through_mcp():
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
        )

        response = await runtime.run(
            "Why is LAB-PC slow?"
        )

    assert response == "System health evidence received."

@pytest.mark.anyio
async def test_agent_runtime_blocks_disallowed_tool_before_execution():
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
    )

    with pytest.raises(
        PermissionError,
        match="Tool is not allowed by policy: run_powershell",
    ):
        await runtime.run(
            "Run PowerShell on LAB-PC"
        )

    assert executed_calls == []


@pytest.mark.anyio
async def test_agent_runtime_blocks_disallowed_target_before_execution():
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
    )

    with pytest.raises(
        PermissionError,
        match="Target is not allowed by policy: DC01",
    ):
        await runtime.run(
            "Check system health on DC01"
        )

    assert executed_calls == []

@pytest.mark.anyio
async def test_agent_runtime_blocks_unexpected_argument_before_execution():
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
        )

        with pytest.raises(
            ValueError,
            match="Unexpected arguments",
        ):
            await runtime.run(
                "Check LAB-PC and execute this extra script"
            )

    assert executed_calls == []


@pytest.mark.anyio
async def test_agent_runtime_passes_tool_definitions_to_llm():
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
    )

    result = await runtime.run("Check LAB-PC")

    assert result == "Done."
    assert received_definitions == TEST_TOOL_DEFINITIONS