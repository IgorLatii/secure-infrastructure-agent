import pytest

from src.windows_mcp.executors.fake import FakeWindowsExecutor
from src.windows_mcp.models import SystemHealth
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

def test_fake_executor_rejects_unknown_operation():
    executor = FakeWindowsExecutor()

    with pytest.raises(ValueError, match="Unsupported operation"):
        executor.execute(
            target="LAB-PC",
            operation="delete_everything",
        )