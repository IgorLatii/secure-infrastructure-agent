import pytest

from src.windows_mcp.executors.operations import WindowsOperation
from src.windows_mcp.executors.winrm import WinRMExecutor
from src.windows_mcp.transports.base import WindowsTransport
from src.windows_mcp.models import (
    ServiceStatus,
    SystemHealth,
    TopProcesses,
    WindowsEvents,
    ScheduledTasks,
    StartupEntries,
)

class FakeWindowsTransport(WindowsTransport):
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        return """
        {
            "uptime_hours": 48.25,
            "cpu_percent": 23.0,
            "memory": {
                "total_gb": 16.0,
                "used_gb": 8.0,
                "used_percent": 50.0
            },
            "disks": [
                {
                    "drive": "C:",
                    "total_gb": 256.0,
                    "free_gb": 100.0
                }
            ],
            "pending_reboot": false
        }
        """

class FakeProcessWindowsTransport(WindowsTransport):
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        return """
        {
            "top_by_cpu": [
                {
                    "name": "chrome.exe",
                    "pid": 4120,
                    "cpu_percent": 42.0,
                    "memory_mb": 3200.0
                },
                {
                    "name": "Teams.exe",
                    "pid": 5184,
                    "cpu_percent": 18.0,
                    "memory_mb": 1450.0
                }
            ],
            "top_by_memory": [
                {
                    "name": "chrome.exe",
                    "pid": 4120,
                    "cpu_percent": 42.0,
                    "memory_mb": 3200.0
                },
                {
                    "name": "Teams.exe",
                    "pid": 5184,
                    "cpu_percent": 18.0,
                    "memory_mb": 1450.0
                }
            ]
        }
        """

class FakeServiceWindowsTransport(WindowsTransport):
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        return """
        {
            "service_name": "W32Time",
            "display_name": "Windows Time",
            "status": "Running",
            "start_type": "Automatic"
        }
        """

class CapturingServiceWindowsTransport(WindowsTransport):
    def __init__(self):
        self.script: str | None = None

    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        self.script = script

        return """
        {
            "service_name": "W32Time",
            "display_name": "Windows Time",
            "status": "Running",
            "start_type": "Automatic"
        }
        """

class CapturingWindowsEventsTransport(WindowsTransport):
    def __init__(self):
        self.script: str | None = None

    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        self.script = script

        return """
        {
            "events": []
        }
        """

class FakeSecurityEventsTransport(WindowsTransport):
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        return """
        {
            "events": [
                {
                    "event_id": 4624,
                    "provider_name": "Microsoft-Windows-Security-Auditing",
                    "level": "LogAlways",
                    "time_created": "2026-10-31T19:40:26Z",
                    "record_id": 415,
                    "message": "An account was successfully logged on.",
                    "message_truncated": false
                }
            ]
        }
        """

class CapturingScheduledTasksTransport(WindowsTransport):
    def __init__(self):
        self.script: str | None = None

    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        self.script = script

        return """
        {
            "tasks": []
        }
        """

class ScheduledTasksTransport(WindowsTransport):
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        return """
        {
            "tasks": [
                {
                    "task_name": "UpdateTelemetry",
                    "task_path": "\\\\",
                    "state": "Ready",
                    "enabled": true,
                    "actions": [
                        {
                            "execute": "C:\\\\Program Files\\\\Example\\\\update-helper.exe",
                            "arguments": "--background"
                        }
                    ]
                }
            ]
        }
        """

class StartupEntriesTransport(WindowsTransport):
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        return """
        {
            "entries": [
                {
                    "name": "UpdateHelper",
                    "command": "C:\\\\Program Files\\\\Example\\\\update-helper.exe --background",
                    "location": "HKLM\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run",
                    "scope": "Machine",
                    "user_sid": null
                },
                {
                    "name": "UserHelper",
                    "command": "C:\\\\Users\\\\Example\\\\AppData\\\\Local\\\\user-helper.exe",
                    "location": "HKU\\\\S-1-5-21-111-222-333-1001\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run",
                    "scope": "User",
                    "user_sid": "S-1-5-21-111-222-333-1001"
                }
            ]
        }
        """

def test_startup_entries_are_parsed_into_structured_evidence():
    executor = WinRMExecutor(StartupEntriesTransport())

    result = executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.STARTUP_ENTRIES,
        parameters={
            "max_entries": 20,
        },
    )

    assert isinstance(result, StartupEntries)
    assert result.target == "LAB-PC"
    assert len(result.entries) == 2

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

    user_entry = result.entries[1]

    assert user_entry.name == "UserHelper"
    assert (
            user_entry.command
            == r"C:\Users\Example\AppData\Local\user-helper.exe"
    )
    assert user_entry.scope == "User"
    assert user_entry.user_sid == "S-1-5-21-111-222-333-1001"
    assert (
            user_entry.location
            == (
                r"HKU\S-1-5-21-111-222-333-1001"
                r"\Software\Microsoft\Windows\CurrentVersion\Run"
            )
    )

def test_scheduled_tasks_are_parsed_into_structured_evidence():
    executor = WinRMExecutor(ScheduledTasksTransport())

    result = executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.SCHEDULED_TASKS,
        parameters={
            "task_name": None,
            "max_tasks": 20,
        },
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

    assert (
        action.execute
        == r"C:\Program Files\Example\update-helper.exe"
    )
    assert action.arguments == "--background"


def test_scheduled_task_name_is_not_interpolated_into_powershell_source():
    transport = CapturingScheduledTasksTransport()
    executor = WinRMExecutor(transport)

    malicious_task_name = "'; Stop-Computer -Force; #"

    executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.SCHEDULED_TASKS,
        parameters={
            "task_name": malicious_task_name,
            "max_tasks": 20,
        },
    )

    assert transport.script is not None

    assert malicious_task_name not in transport.script
    assert "Stop-Computer" not in transport.script

    assert "FromBase64String" in transport.script
    assert "ConvertFrom-Json" in transport.script

def test_winrm_executor_preserves_log_always_event_level():
    executor = WinRMExecutor(FakeSecurityEventsTransport())

    result = executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.WINDOWS_EVENTS,
        parameters={
            "log_name": "Security",
            "lookback_minutes": 60,
            "max_events": 10,
        },
    )

    assert len(result.events) == 1
    assert result.events[0].event_id == 4624
    assert result.events[0].level == "LogAlways"

def test_windows_event_provider_is_not_interpolated_into_powershell_source():
    transport = CapturingWindowsEventsTransport()
    executor = WinRMExecutor(transport)

    malicious_provider = "'; Stop-Computer -Force; #"

    executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.WINDOWS_EVENTS,
        parameters={
            "log_name": "System",
            "lookback_minutes": 60,
            "provider_name": malicious_provider,
            "max_events": 20,
        },
    )

    assert transport.script is not None

    assert malicious_provider not in transport.script
    assert "Stop-Computer" not in transport.script

    assert "FromBase64String" in transport.script
    assert "ConvertFrom-Json" in transport.script

class FakeWindowsEventsTransport(WindowsTransport):
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        return """
        {
            "events": [
                {
                    "event_id": 7036,
                    "provider_name": "Service Control Manager",
                    "level": "Information",
                    "time_created": "2026-10-31T12:00:00Z",
                    "record_id": 12345,
                    "message": "The Windows Time service entered the running state.",
                    "message_truncated": false
                }
            ]
        }
        """

def test_winrm_executor_returns_structured_windows_events():
    executor = WinRMExecutor(FakeWindowsEventsTransport())

    result = executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.WINDOWS_EVENTS,
        parameters={
            "log_name": "System",
            "lookback_minutes": 60,
            "levels": ["Information"],
            "event_ids": [7036],
            "provider_name": "Service Control Manager",
            "max_events": 20,
        },
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
    assert (
        event.message
        == "The Windows Time service entered the running state."
    )
    assert event.message_truncated is False

def test_winrm_executor_returns_structured_system_health():
    executor = WinRMExecutor(FakeWindowsTransport())

    health = executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.SYSTEM_HEALTH,
    )

    assert isinstance(health, SystemHealth)
    assert health.target == "LAB-PC"
    assert health.uptime_hours == 48.25
    assert health.cpu_percent == 23.0
    assert health.memory.used_percent == 50.0
    assert health.disks[0].drive == "C:"
    assert health.pending_reboot is False


def test_winrm_executor_returns_structured_top_processes():
    executor = WinRMExecutor(FakeProcessWindowsTransport())

    result = executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.TOP_PROCESSES,
    )

    assert isinstance(result, TopProcesses)
    assert result.target == "LAB-PC"

    assert len(result.top_by_cpu) == 2
    assert len(result.top_by_memory) == 2

    assert result.top_by_cpu[0].name == "chrome.exe"
    assert result.top_by_cpu[0].pid == 4120
    assert result.top_by_cpu[0].cpu_percent == 42.0

    assert result.top_by_memory[0].name == "chrome.exe"
    assert result.top_by_memory[0].memory_mb == 3200.0

def test_winrm_executor_returns_structured_service_status():
    executor = WinRMExecutor(FakeServiceWindowsTransport())

    result = executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.SERVICE_STATUS,
        parameters={
            "service_name": "W32Time",
        },
    )

    assert isinstance(result, ServiceStatus)
    assert result.target == "LAB-PC"
    assert result.service_name == "W32Time"
    assert result.display_name == "Windows Time"
    assert result.status == "Running"
    assert result.start_type == "Automatic"

def test_winrm_executor_rejects_unknown_operation():
    executor = WinRMExecutor(FakeWindowsTransport())

    with pytest.raises(ValueError, match="Unsupported operation"):
        executor.execute(
            target="LAB-PC",
            operation="delete_everything",
        )

def test_service_name_is_not_interpolated_into_powershell_source():
    transport = CapturingServiceWindowsTransport()
    executor = WinRMExecutor(transport)

    malicious_service_name = "'; Stop-Service Spooler; #"

    executor.execute(
        target="LAB-PC",
        operation=WindowsOperation.SERVICE_STATUS,
        parameters={
            "service_name": malicious_service_name,
        },
    )

    assert transport.script is not None

    assert malicious_service_name not in transport.script
    assert "Stop-Service Spooler" not in transport.script

    assert "FromBase64String" in transport.script

def test_startup_entries_rejects_invalid_max_entries():
    executor = WinRMExecutor(ScheduledTasksTransport())

    with pytest.raises(
        ValueError,
        match="max_entries must be an integer between 1 and 100",
    ):
        executor.execute(
            target="LAB-PC",
            operation=WindowsOperation.STARTUP_ENTRIES,
            parameters={
                "max_entries": 101,
            },
        )

@pytest.mark.parametrize(
    "invalid_max_entries",
    [True, False, 0, 101, 1.5, "50"],
)
def test_startup_entries_rejects_invalid_max_entries_types(
        invalid_max_entries,
):
    executor = WinRMExecutor(ScheduledTasksTransport())

    with pytest.raises(ValueError):
        executor.execute(
            target="LAB-PC",
            operation=WindowsOperation.STARTUP_ENTRIES,
            parameters={
                "max_entries": invalid_max_entries,
            },
        )