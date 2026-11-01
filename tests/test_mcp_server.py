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
    assert "get_windows_events" in tool_names
    assert "get_process_details" in tool_names


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
async def test_mcp_calls_windows_events_tool():
    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool(
            "get_windows_events",
            {
                "target": "LAB-PC",
                "log_name": "System",
                "lookback_minutes": 60,
                "levels": ["Information"],
                "max_events": 20,
            },
        )

    assert result.is_error is False

    windows_events = result.structured_content

    assert windows_events is not None
    assert windows_events["target"] == "LAB-PC"
    assert windows_events["log_name"] == "System"
    assert windows_events["lookback_minutes"] == 60

    assert len(windows_events["events"]) == 1

    event = windows_events["events"][0]

    assert event["event_id"] == 7036
    assert event["provider_name"] == "Service Control Manager"
    assert event["level"] == "Information"
    assert event["time_created"] == "2026-10-31T12:00:00Z"
    assert event["record_id"] == 12345
    assert (
        event["message"]
        == "The Windows Time service entered the running state."
    )
    assert event["message_truncated"] is False

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


@pytest.mark.anyio
async def test_mcp_calls_scheduled_tasks_tool():
    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool(
            "get_scheduled_tasks",
            {
                "target": "LAB-PC",
                "max_tasks": 20,
            },
        )

    assert result.is_error is False

    scheduled_tasks = result.structured_content

    assert scheduled_tasks is not None
    assert scheduled_tasks["target"] == "LAB-PC"

    assert len(scheduled_tasks["tasks"]) == 1

    task = scheduled_tasks["tasks"][0]

    assert task["task_name"] == "UpdateTelemetry"
    assert task["task_path"] == "\\"
    assert task["state"] == "Ready"
    assert task["enabled"] is True
    assert len(task["actions"]) == 1

    action = task["actions"][0]

    assert (
            action["execute"]
            == r"C:\Program Files\Example\update-helper.exe"
    )
    assert action["arguments"] == "--background"

@pytest.mark.anyio
async def test_mcp_calls_startup_entries_tool():
    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool(
            "get_startup_entries",
            {
                "target": "LAB-PC",
                "max_entries": 20,
            },
        )

    assert result.is_error is False

    startup_entries = result.structured_content

    assert startup_entries is not None
    assert startup_entries["target"] == "LAB-PC"

    assert len(startup_entries["entries"]) == 1

    entry = startup_entries["entries"][0]

    assert entry["name"] == "UpdateHelper"
    assert (
        entry["command"]
        == r"C:\Program Files\Example\update-helper.exe --background"
    )
    assert (
        entry["location"]
        == r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run"
    )
    assert entry["scope"] == "Machine"
    assert entry["user_sid"] is None

@pytest.mark.anyio
async def test_mcp_calls_network_connections_tool():

    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool(
            "get_network_connections",
            {
                "target": "LAB-PC",
                "max_connections": 20,
            },
        )

    assert result.is_error is False

    network_connections = result.structured_content
    assert network_connections is not None
    assert network_connections["target"] == "LAB-PC"
    assert len(network_connections["connections"]) == 1

    connection = network_connections["connections"][0]

    assert connection["local_address"] == "192.0.2.10"
    assert connection["local_port"] == 51422
    assert connection["remote_address"] == "203.0.113.50"
    assert connection["remote_port"] == 443
    assert connection["state"] == "Established"
    assert connection["pid"] == 4820
    assert connection["process_name"] == "update-helper.exe"

    @pytest.mark.anyio
    async def test_mcp_calls_process_details_tool():
        server = create_server()

        async with Client(server) as client:
            result = await client.call_tool(
                "get_process_details",
                {
                    "target": "LAB-PC",
                    "pid": 4820,
                },
            )

        assert result.is_error is False

        process_details = result.structured_content

        assert process_details is not None
        assert process_details["target"] == "LAB-PC"
        assert process_details["pid"] == 4820
        assert process_details["name"] == "update-helper.exe"
        assert (
                process_details["executable_path"]
                == r"C:\Program Files\Example\update-helper.exe"
        )
        assert (
                process_details["command_line"]
                == r'"C:\Program Files\Example\update-helper.exe" --background'
        )
        assert process_details["parent_pid"] == 1200
        assert process_details["user"] == r"LAB\analyst"
        assert process_details["start_time"] == "2026-11-01T08:30:00Z"