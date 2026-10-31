import pytest

from src.windows_mcp.executors.fake import FakeWindowsExecutor
from src.windows_mcp.models import SystemHealth, TopProcesses
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