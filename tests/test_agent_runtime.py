import pytest

from src.agent.fake_llm import FakeAgentLLM
from src.agent.models import ToolCall, ToolResult
from src.agent.runtime import AgentRuntime

from mcp.client import Client
from src.agent.mcp_executor import MCPToolExecutor
from src.windows_mcp.server import create_server
from src.agent.policy.tool_policy import ToolPolicy




@pytest.mark.anyio
async def test_agent_runtime_executes_tool_and_returns_final_response():
    executed_calls: list[ToolCall] = []

    async def fake_tool_executor(call: ToolCall) -> ToolResult:
        executed_calls.append(call)

        return ToolResult(
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
        def decide(
            self,
            user_request: str,
            tool_results: list[ToolResult],
        ) -> ToolCall | str:
            return ToolCall(
                name="get_system_health",
                arguments={"target": "LAB-PC"},
            )

    executed_calls: list[ToolCall] = []

    async def fake_tool_executor(call: ToolCall) -> ToolResult:
        executed_calls.append(call)

        return ToolResult(
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

        runtime = AgentRuntime(
            llm=FakeAgentLLM(),
            tool_executor=mcp_executor.execute,
            policy=ToolPolicy(
                allowed_tools={"get_system_health"},
                allowed_targets={"LAB-PC"},
            ),
        )

        response = await runtime.run(
            "Why is LAB-PC slow?"
        )

    assert response == "System health evidence received."

@pytest.mark.anyio
async def test_agent_runtime_blocks_disallowed_tool_before_execution():
    class UnsafeToolLLM:
        def decide(self, user_request, tool_results):
            return ToolCall(
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
        def decide(self, user_request, tool_results):
            return ToolCall(
                name="get_system_health",
                arguments={"target": "DC01"},
            )

    executed_calls = []

    async def fake_tool_executor(call):
        executed_calls.append(call)

        return ToolResult(
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
    )

    with pytest.raises(
        PermissionError,
        match="Target is not allowed by policy: DC01",
    ):
        await runtime.run(
            "Check system health on DC01"
        )

    assert executed_calls == []