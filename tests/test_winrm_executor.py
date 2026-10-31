import pytest

from src.windows_mcp.executors.operations import WindowsOperation
from src.windows_mcp.executors.winrm import WinRMExecutor
from src.windows_mcp.transports.base import WindowsTransport
from src.windows_mcp.models import ServiceStatus, SystemHealth, TopProcesses

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