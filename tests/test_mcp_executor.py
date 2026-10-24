import pytest

from src.agent.mcp_executor import MCPToolExecutor
from src.agent.models import ToolCall


class FakeMCPResult:
    is_error = False
    structured_content = {
        "target": "LAB-PC",
        "cpu_percent": 12.5,
    }


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return FakeMCPResult()


@pytest.mark.anyio
async def test_mcp_tool_executor_calls_mcp_client():
    client = FakeMCPClient()
    executor = MCPToolExecutor(client)

    call = ToolCall(
        name="get_system_health",
        arguments={"target": "LAB-PC"},
    )

    result = await executor.execute(call)

    assert client.calls == [
        ("get_system_health", {"target": "LAB-PC"})
    ]

    assert result.name == "get_system_health"
    assert result.content == {
        "target": "LAB-PC",
        "cpu_percent": 12.5,
    }

@pytest.mark.anyio
async def test_mcp_tool_executor_rejects_mcp_error():
    class ErrorMCPResult:
        is_error = True
        structured_content = None

    class ErrorMCPClient:
        async def call_tool(self, name, arguments):
            return ErrorMCPResult()

    executor = MCPToolExecutor(ErrorMCPClient())

    call = ToolCall(
        name="get_system_health",
        arguments={"target": "LAB-PC"},
    )

    with pytest.raises(
        RuntimeError,
        match="MCP tool execution failed: get_system_health",
    ):
        await executor.execute(call)


@pytest.mark.anyio
async def test_mcp_tool_executor_rejects_missing_structured_content():
    class EmptyMCPResult:
        is_error = False
        structured_content = None

    class EmptyMCPClient:
        async def call_tool(self, name, arguments):
            return EmptyMCPResult()

    executor = MCPToolExecutor(EmptyMCPClient())

    call = ToolCall(
        name="get_system_health",
        arguments={"target": "LAB-PC"},
    )

    with pytest.raises(
        RuntimeError,
        match="MCP tool returned no structured content: get_system_health",
    ):
        await executor.execute(call)