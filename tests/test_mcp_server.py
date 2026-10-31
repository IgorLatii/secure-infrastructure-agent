import pytest

from mcp.client import Client
from src.windows_mcp.executors.fake import FakeWindowsExecutor


from src.windows_mcp.server import create_server


@pytest.mark.anyio
async def test_mcp_exposes_diagnostic_tools():
    server = create_server()

    async with Client(server) as client:
        result = await client.list_tools()

    tool_names = [tool.name for tool in result.tools]

    assert "get_system_health" in tool_names
    assert "get_top_processes" in tool_names
    assert "get_service_status" in tool_names

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
async def test_mcp_calls_top_processes_tool():
    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool(
            "get_top_processes",
            {"target": "LAB-PC"},
        )

    assert result.is_error is False

    top_processes = result.structured_content

    assert top_processes is not None
    assert top_processes["target"] == "LAB-PC"

    assert len(top_processes["top_by_cpu"]) == 3
    assert len(top_processes["top_by_memory"]) == 3

    top_cpu = top_processes["top_by_cpu"][0]

    assert top_cpu["name"] == "chrome.exe"
    assert top_cpu["pid"] == 4120
    assert top_cpu["cpu_percent"] == 42.0
    assert top_cpu["memory_mb"] == 3200.0

    top_memory = top_processes["top_by_memory"][0]

    assert top_memory["name"] == "chrome.exe"
    assert top_memory["memory_mb"] == 3200.0

@pytest.mark.anyio
async def test_mcp_calls_service_status_tool():
    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool(
            "get_service_status",
            {
                "target": "LAB-PC",
                "service_name": "W32Time",
            },
        )

    assert result.is_error is False

    service_status = result.structured_content

    assert service_status is not None
    assert service_status["target"] == "LAB-PC"
    assert service_status["service_name"] == "W32Time"
    assert service_status["display_name"] == "Windows Time"
    assert service_status["status"] == "Running"
    assert service_status["start_type"] == "Automatic"

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
