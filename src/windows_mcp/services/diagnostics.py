from ..executors.base import WindowsExecutor
from ..executors.operations import WindowsOperation
from ..models import (
    ScheduledTasks,
    ServiceStatus,
    SystemHealth,
    TopProcesses,
    WindowsEvents,
    StartupEntries,
    NetworkConnections,
)


class DiagnosticService:
    """
    Application service responsible for Windows diagnostics.

    It defines what diagnostic operation should be performed,
    while the executor defines how data is obtained.
    """

    def __init__(self, executor: WindowsExecutor):
        self.executor = executor

    def get_system_health(self, target: str) -> SystemHealth:
        return self.executor.execute(
            target=target,
            operation=WindowsOperation.SYSTEM_HEALTH,
        )

    def get_top_processes(self, target: str) -> TopProcesses:
        return self.executor.execute(
            target=target,
            operation=WindowsOperation.TOP_PROCESSES,
        )

    def get_service_status(
            self,
            target: str,
            service_name: str,
    ) -> ServiceStatus:
        return self.executor.execute(
            target=target,
            operation=WindowsOperation.SERVICE_STATUS,
            parameters={
                "service_name": service_name,
            },
        )

    def get_windows_events(
            self,
            target: str,
            log_name: str,
            lookback_minutes: int,
            levels: list[str] | None = None,
            event_ids: list[int] | None = None,
            provider_name: str | None = None,
            max_events: int = 50,
    ) -> WindowsEvents:
        return self.executor.execute(
            target=target,
            operation=WindowsOperation.WINDOWS_EVENTS,
            parameters={
                "log_name": log_name,
                "lookback_minutes": lookback_minutes,
                "levels": levels,
                "event_ids": event_ids,
                "provider_name": provider_name,
                "max_events": max_events,
            },
        )

    def get_scheduled_tasks(
            self,
            target: str,
            task_name: str | None = None,
            max_tasks: int = 50,
    ) -> ScheduledTasks:
        return self.executor.execute(
            target=target,
            operation=WindowsOperation.SCHEDULED_TASKS,
            parameters={
                "task_name": task_name,
                "max_tasks": max_tasks,
            },
        )

    def get_startup_entries(
            self,
            target: str,
            max_entries: int = 50,
    ) -> StartupEntries:
        return self.executor.execute(
            target=target,
            operation=WindowsOperation.STARTUP_ENTRIES,
            parameters={
                "max_entries": max_entries,
            },
        )

    def get_network_connections(
            self,
            target: str,
            max_connections: int = 50,
    ) -> NetworkConnections:
        return self.executor.execute(
            target=target,
            operation=WindowsOperation.NETWORK_CONNECTIONS,
            parameters={
                "max_connections": max_connections,
            },
        )