import pytest

from mcp.client import Client
from src.windows_mcp.executors.fake import FakeWindowsExecutor


from src.windows_mcp.server import create_server


@pytest.mark.anyio
async def test_mcp_exposes_system_health_tool():
    server = create_server()

    async with Client(server) as client:
        result = await client.list_tools()

    tool_names = [tool.name for tool in result.tools]

    assert "get_system_health" in tool_names


@pytest.mark.anyio
async def test_mcp_calls_system_health_tool():
    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool(
            "get_system_health",
            {"target": "LAB-PC"},
        )

    assert result.is_error is False

    health = result.structured_content

    assert health is not None
    assert health["target"] == "LAB-PC"
    assert health["cpu_percent"] == 87.0
    assert health["memory"]["used_percent"] == 88.75
    assert health["disks"][0]["drive"] == "C:"
    assert health["pending_reboot"] is False


@pytest.mark.anyio
async def test_mcp_uses_injected_executor():
    executor = FakeWindowsExecutor()
    server = create_server(executor=executor)

    async with Client(server) as client:
        result = await client.call_tool(
            "get_system_health",
            {"target": "INJECTED-PC"},
        )

    health = result.structured_content

    assert health is not None
    assert health["target"] == "INJECTED-PC"
    assert health["cpu_percent"] == 87.0
