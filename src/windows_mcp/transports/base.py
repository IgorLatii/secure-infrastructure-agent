from abc import ABC, abstractmethod


class WindowsTransport(ABC):
    """
    Abstract transport for executing predefined remote
    diagnostic commands on Windows targets.
    """

    @abstractmethod
    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        """
        Execute PowerShell on a Windows target and return
        its textual output.
        """
        raise NotImplementedError