from dataclasses import dataclass, field


@dataclass(frozen=True)
class WinRMConnectionConfig:
    """
    Configuration required to establish a WinRM connection.

    Secrets are supplied at runtime and must never be exposed
    through MCP tools, logs, or diagnostic results.
    """

    username: str
    password: str = field(repr=False)
    auth: str = "ntlm"
    port: int = 5985
    use_ssl: bool = False
    verify_cert: bool = True