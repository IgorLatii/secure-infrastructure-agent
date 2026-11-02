from typing import Any

from ..base import WindowsExecutor
from ..operations import WindowsOperation
from ...transports.base import WindowsTransport

from .health import get_system_health
from .processes import get_top_processes
from .service_status import get_service_status
from .events import get_windows_events
from .tasks import get_scheduled_tasks
from .startup import get_startup_entries
from .network import get_network_connections
from .process_details import get_process_details


class WinRMExecutor(WindowsExecutor):
    """
    Windows executor that obtains diagnostic data
    through an injected Windows transport.

    Only explicitly supported diagnostic operations are dispatched
    to predefined handlers.
    """

    def __init__(self, transport: WindowsTransport):
        self._transport = transport

    def execute(
            self,
            target: str,
            operation: WindowsOperation,
            parameters: dict[str, Any] | None = None,
    ) -> Any:
        handlers = {
            WindowsOperation.SYSTEM_HEALTH: get_system_health,
            WindowsOperation.TOP_PROCESSES: get_top_processes,
            WindowsOperation.SERVICE_STATUS: get_service_status,
            WindowsOperation.WINDOWS_EVENTS: get_windows_events,
            WindowsOperation.SCHEDULED_TASKS: get_scheduled_tasks,
            WindowsOperation.STARTUP_ENTRIES: get_startup_entries,
            WindowsOperation.NETWORK_CONNECTIONS: get_network_connections,
            WindowsOperation.PROCESS_DETAILS: get_process_details,
        }

        try:
            handler = handlers[operation]
        except KeyError:
            raise ValueError(
                f"Unsupported operation: {operation}"
            ) from None

        return handler(
            self._transport,
            target,
            parameters,
        )