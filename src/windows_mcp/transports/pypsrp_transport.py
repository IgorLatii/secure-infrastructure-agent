from pypsrp.client import Client

from ..config import WinRMConnectionConfig
from .base import WindowsTransport


class PyPSRPTransport(WindowsTransport):
    """
    WinRM transport implemented with pypsrp.
    """

    def __init__(self, config: WinRMConnectionConfig):
        self._config = config

    def run_powershell(
        self,
        target: str,
        script: str,
    ) -> str:
        with Client(
            target,
            username=self._config.username,
            password=self._config.password,
            auth=self._config.auth,
            port=self._config.port,
            ssl=self._config.use_ssl,
            cert_validation=self._config.verify_cert,
        ) as client:
            output, streams, had_errors = client.execute_ps(script)

        if had_errors:
            raise RuntimeError(
                f"PowerShell execution failed on target {target}"
            )

        return str(output).strip()