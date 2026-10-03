from abc import ABC, abstractmethod
from typing import Any


class WindowsExecutor(ABC):
    """
    Abstract interface for obtaining diagnostic data
    from a Windows target.

    Implementations may use fake data, WinRM, or another
    execution mechanism.
    """

    @abstractmethod
    def execute(self, target: str, operation: str) -> Any:
        """
        Execute a predefined diagnostic operation against a target.

        Args:
            target: Logical Windows target name.
            operation: Predefined diagnostic operation identifier.

        Returns:
            Operation-specific diagnostic data.
        """
        raise NotImplementedError