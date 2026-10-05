from enum import Enum


class WindowsOperation(str, Enum):
    """
    Diagnostic operations supported by Windows executors.

    Only explicitly defined operations may cross the executor boundary.
    """

    SYSTEM_HEALTH = "system_health"