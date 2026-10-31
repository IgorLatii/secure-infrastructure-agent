from typing import Any

from .base import WindowsExecutor
from .operations import WindowsOperation
from ..models import (
    DiskInfo,
    MemoryInfo,
    ProcessInfo,
    ServiceStatus,
    SystemHealth,
    TopProcesses,
)


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
        parameters: dict[str, Any] | None = None,
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

        if operation is WindowsOperation.TOP_PROCESSES:
            processes = [
                ProcessInfo(
                    name="chrome.exe",
                    pid=4120,
                    cpu_percent=42.0,
                    memory_mb=3200.0,
                ),
                ProcessInfo(
                    name="Teams.exe",
                    pid=5184,
                    cpu_percent=18.0,
                    memory_mb=1450.0,
                ),
                ProcessInfo(
                    name="explorer.exe",
                    pid=2260,
                    cpu_percent=2.0,
                    memory_mb=180.0,
                ),
            ]

            return TopProcesses(
                target=target,
                top_by_cpu=sorted(
                    processes,
                    key=lambda process: process.cpu_percent,
                    reverse=True,
                ),
                top_by_memory=sorted(
                    processes,
                    key=lambda process: process.memory_mb,
                    reverse=True,
                ),
            )

        if operation is WindowsOperation.SERVICE_STATUS:
            if parameters is None or "service_name" not in parameters:
                raise ValueError(
                    "SERVICE_STATUS requires parameter: service_name"
                )

            service_name = parameters["service_name"]

            return ServiceStatus(
                target=target,
                service_name=service_name,
                display_name="Windows Time",
                status="Running",
                start_type="Automatic",
            )

        raise ValueError(f"Unsupported operation: {operation}")