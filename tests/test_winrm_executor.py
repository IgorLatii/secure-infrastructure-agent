import pytest

from src.windows_mcp.executors.operations import WindowsOperation
from src.windows_mcp.executors.winrm import WinRMExecutor
from src.windows_mcp.transports.base import WindowsTransport
from src.windows_mcp.models import SystemHealth


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


def test_winrm_executor_rejects_unknown_operation():
    executor = WinRMExecutor(FakeWindowsTransport())

    with pytest.raises(ValueError, match="Unsupported operation"):
        executor.execute(
            target="LAB-PC",
            operation="delete_everything",
        )