from ..executors.base import WindowsExecutor
from ..executors.operations import WindowsOperation
from ..models import SystemHealth


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