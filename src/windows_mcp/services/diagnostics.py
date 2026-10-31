from ..executors.base import WindowsExecutor
from ..executors.operations import WindowsOperation
from ..models import ServiceStatus, SystemHealth, TopProcesses


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