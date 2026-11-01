import pytest

from src.windows_mcp.executors.fake import FakeWindowsExecutor
from src.windows_mcp.models import (
    ScheduledTasks,
    ServiceStatus,
    SystemHealth,
    TopProcesses,
    WindowsEvents,
    StartupEntries,
    NetworkConnections,
)
from src.windows_mcp.services.diagnostics import DiagnosticService


def test_get_system_health_returns_structured_health():
    service = DiagnosticService(FakeWindowsExecutor())

    health = service.get_system_health("LAB-PC")

    assert isinstance(health, SystemHealth)
    assert health.target == "LAB-PC"
    assert health.cpu_percent == 87.0
    assert health.memory.used_percent == 88.75
    assert health.disks[0].drive == "C:"
    assert health.pending_reboot is False

def test_get_top_processes_returns_structured_processes():
    service = DiagnosticService(FakeWindowsExecutor())

    result = service.get_top_processes("LAB-PC")

    assert isinstance(result, TopProcesses)
    assert result.target == "LAB-PC"

    assert len(result.top_by_cpu) == 3
    assert len(result.top_by_memory) == 3

    assert result.top_by_cpu[0].name == "chrome.exe"
    assert result.top_by_cpu[0].cpu_percent == 42.0

    assert result.top_by_memory[0].name == "chrome.exe"
    assert result.top_by_memory[0].memory_mb == 3200.0


def test_fake_executor_rejects_unknown_operation():
    executor = FakeWindowsExecutor()

    with pytest.raises(ValueError, match="Unsupported operation"):
        executor.execute(
            target="LAB-PC",
            operation="delete_everything",
        )

def test_get_service_status_returns_structured_status():
    service = DiagnosticService(FakeWindowsExecutor())

    result = service.get_service_status(
        target="LAB-PC",
        service_name="W32Time",
    )

    assert isinstance(result, ServiceStatus)
    assert result.target == "LAB-PC"
    assert result.service_name == "W32Time"
    assert result.display_name == "Windows Time"
    assert result.status == "Running"
    assert result.start_type == "Automatic"

def test_get_windows_events_returns_structured_events():
    service = DiagnosticService(FakeWindowsExecutor())

    result = service.get_windows_events(
        target="LAB-PC",
        log_name="System",
        lookback_minutes=60,
        levels=["Information"],
        max_events=20,
    )

    assert isinstance(result, WindowsEvents)
    assert result.target == "LAB-PC"
    assert result.log_name == "System"
    assert result.lookback_minutes == 60

    assert len(result.events) == 1

    event = result.events[0]

    assert event.event_id == 7036
    assert event.provider_name == "Service Control Manager"
    assert event.level == "Information"
    assert event.time_created == "2026-10-31T12:00:00Z"
    assert event.record_id == 12345
    assert event.message == "The Windows Time service entered the running state."
    assert event.message_truncated is False

def test_get_scheduled_tasks_returns_structured_tasks():
    service = DiagnosticService(FakeWindowsExecutor())

    result = service.get_scheduled_tasks(
        target="LAB-PC",
        max_tasks=20,
    )

    assert isinstance(result, ScheduledTasks)
    assert result.target == "LAB-PC"

    assert len(result.tasks) == 1

    task = result.tasks[0]

    assert task.task_name == "UpdateTelemetry"
    assert task.task_path == "\\"
    assert task.state == "Ready"
    assert task.enabled is True

    assert len(task.actions) == 1

    action = task.actions[0]

    assert action.execute == r"C:\Program Files\Example\update-helper.exe"
    assert action.arguments == "--background"


def test_get_startup_entries_returns_structured_entries():
    service = DiagnosticService(FakeWindowsExecutor())

    result = service.get_startup_entries(
        target="LAB-PC",
        max_entries=20,
    )

    assert isinstance(result, StartupEntries)
    assert result.target == "LAB-PC"
    assert len(result.entries) == 1

    entry = result.entries[0]

    assert entry.name == "UpdateHelper"
    assert (
        entry.command
        == r"C:\Program Files\Example\update-helper.exe --background"
    )
    assert (
        entry.location
        == r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run"
    )
    assert entry.scope == "Machine"
    assert entry.user_sid is None

def test_get_network_connections_returns_structured_connections():
    service = DiagnosticService(FakeWindowsExecutor())

    result = service.get_network_connections(
        target="LAB-PC",
        max_connections=20,
    )

    assert isinstance(result, NetworkConnections)
    assert result.target == "LAB-PC"
    assert len(result.connections) == 1

    connection = result.connections[0]

    assert connection.local_address == "192.0.2.10"
    assert connection.local_port == 51422
    assert connection.remote_address == "203.0.113.50"
    assert connection.remote_port == 443
    assert connection.state == "Established"
    assert connection.pid == 4820
    assert connection.process_name == "update-helper.exe"