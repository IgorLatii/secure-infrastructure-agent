from typing import Any

from .base import WindowsExecutor
from .operations import WindowsOperation
from ..models import DiskInfo, MemoryInfo, SystemHealth


class FakeWindowsExecutor(WindowsExecutor):
    """
    Deterministic executor used during development and testing.

    It returns predefined diagnostic data without contacting
    a real Windows host.
    """

    def execute(
        self,
        target: str,
        operation: WindowsOperation,
    ) -> Any:
        if operation is WindowsOperation.SYSTEM_HEALTH:
            return SystemHealth(
                target=target,
                uptime_hours=72.5,
                cpu_percent=87.0,
                memory=MemoryInfo(
                    total_gb=16.0,
                    used_gb=14.2,
                    used_percent=88.75,
                ),
                disks=[
                    DiskInfo(
                        drive="C:",
                        total_gb=256.0,
                        free_gb=11.5,
                    )
                ],
                pending_reboot=False,
            )

        raise ValueError(f"Unsupported operation: {operation}")