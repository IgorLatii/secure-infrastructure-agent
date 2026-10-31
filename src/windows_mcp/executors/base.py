from abc import ABC, abstractmethod
from typing import Any

from .operations import WindowsOperation


class WindowsExecutor(ABC):
    """
    Abstract interface for obtaining diagnostic data
    from a Windows target.

    Implementations may use fake data, WinRM, or another
    execution mechanism.
    """

    @abstractmethod
    def execute(
        self,
        target: str,
        operation: WindowsOperation,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a predefined diagnostic operation against a target.

        Args:
            target: Logical Windows target name.
            operation: Explicitly supported diagnostic operation.
            parameters: Operation-specific structured parameters.

        Returns:
            Operation-specific diagnostic data.
        """
        raise NotImplementedError