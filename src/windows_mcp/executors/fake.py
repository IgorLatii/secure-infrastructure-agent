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
    WindowsEvent,
    WindowsEvents,
    ScheduledTask,
    ScheduledTasks,
    ScheduledTaskAction,
    StartupEntry,
    StartupEntries,
    NetworkConnection,
    NetworkConnections,
    ProcessDetails,
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

        if operation is WindowsOperation.WINDOWS_EVENTS:
            if parameters is None:
                raise ValueError(
                    "WINDOWS_EVENTS requires parameters"
                )

            return WindowsEvents(
                target=target,
                log_name=parameters["log_name"],
                lookback_minutes=parameters["lookback_minutes"],
                events=[
                    WindowsEvent(
                        event_id=7036,
                        provider_name="Service Control Manager",
                        level="Information",
                        time_created="2026-10-31T12:00:00Z",
                        record_id=12345,
                        message=(
                            "The Windows Time service entered "
                            "the running state."
                        ),
                        message_truncated=False,
                    )
                ],
            )

        if operation is WindowsOperation.SCHEDULED_TASKS:
            if parameters is None:
                raise ValueError(
                    "SCHEDULED_TASKS requires parameters"
                )

            return ScheduledTasks(
                target=target,
                tasks=[
                    ScheduledTask(
                        task_name="UpdateTelemetry",
                        task_path="\\",
                        state="Ready",
                        enabled=True,
                        actions=[
                            ScheduledTaskAction(
                                execute=r"C:\Program Files\Example\update-helper.exe",
                                arguments="--background",
                            )
                        ],
                    )
                ],
            )

        if operation is WindowsOperation.STARTUP_ENTRIES:
            if parameters is None:
                raise ValueError(
                    "STARTUP_ENTRIES requires parameters"
                )

            return StartupEntries(
                target=target,
                entries=[
                    StartupEntry(
                        name="UpdateHelper",
                        command=(
                            r"C:\Program Files\Example\update-helper.exe "
                            r"--background"
                        ),
                        location=(
                            r"HKLM\Software\Microsoft\Windows"
                            r"\CurrentVersion\Run"
                        ),
                        scope="Machine",
                        user_sid=None,
                    )
                ],
            )

        if operation is WindowsOperation.NETWORK_CONNECTIONS:
            if parameters is None:
                raise ValueError(
                    "NETWORK_CONNECTIONS requires parameters"
                )

            return NetworkConnections(
                target=target,
                connections=[
                    NetworkConnection(
                        local_address="192.0.2.10",
                        local_port=51422,
                        remote_address="203.0.113.50",
                        remote_port=443,
                        state="Established",
                        pid=4820,
                        process_name="update-helper.exe",
                    )
                ],
            )

        if operation is WindowsOperation.PROCESS_DETAILS:
            if parameters is None or "pid" not in parameters:
                raise ValueError(
                    "PROCESS_DETAILS requires parameter: pid"
                )

            pid = parameters["pid"]

            return ProcessDetails(
                target=target,
                pid=pid,
                name="update-helper.exe",
                executable_path=r"C:\Program Files\Example\update-helper.exe",
                command_line=(
                    r'"C:\Program Files\Example\update-helper.exe" --background'
                ),
                parent_pid=1200,
                user=r"LAB\analyst",
                start_time="2026-11-01T08:30:00Z",
            )

        raise ValueError(f"Unsupported operation: {operation}")