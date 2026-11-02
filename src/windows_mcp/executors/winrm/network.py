import json
from typing import Any

from ...models import NetworkConnection, NetworkConnections
from ...transports.base import WindowsTransport


def get_network_connections(
        transport: WindowsTransport,
        target: str,
        parameters: dict[str, Any] | None,
) -> NetworkConnections:
    if parameters is None:
        raise ValueError(
            "NETWORK_CONNECTIONS requires parameters"
        )

    max_connections = parameters.get("max_connections", 50)

    if isinstance(max_connections, bool) or not isinstance(max_connections, int):
        raise ValueError(
            "max_connections must be an integer"
        )

    if not 1 <= max_connections <= 100:
        raise ValueError(
            "max_connections must be between 1 and 100"
        )

    script = f"""
    $connections = Get-NetTCPConnection -ErrorAction SilentlyContinue |
        Sort-Object @{{
            Expression = {{
                if ($_.State -eq "Established") {{ 0 }}
                elseif ($_.State -eq "Listen") {{ 2 }}
                else {{ 1 }}
            }}
        }} |
        Select-Object -First {max_connections}

    $result = foreach ($connection in $connections) {{
        $processName = ""

        if ($connection.OwningProcess -gt 0) {{
            $process = Get-Process `
                -Id $connection.OwningProcess `
                -ErrorAction SilentlyContinue

            if ($null -ne $process) {{
                $processName = $process.ProcessName + ".exe"
            }}
        }}

        [PSCustomObject]@{{
            local_address = [string]$connection.LocalAddress
            local_port = [int]$connection.LocalPort
            remote_address = [string]$connection.RemoteAddress
            remote_port = [int]$connection.RemotePort
            state = [string]$connection.State
            pid = [int]$connection.OwningProcess
            process_name = $processName
        }}
    }}

    @{{
        connections = @($result)
    }} | ConvertTo-Json -Depth 4 -Compress
    """

    raw_output = transport.run_powershell(
        target=target,
        script=script,
    )

    data = json.loads(raw_output)

    connections = [
        NetworkConnection(
            local_address=item["local_address"],
            local_port=item["local_port"],
            remote_address=item["remote_address"],
            remote_port=item["remote_port"],
            state=item["state"],
            pid=item["pid"],
            process_name=item["process_name"],
        )
        for item in data["connections"]
    ]

    return NetworkConnections(
        target=target,
        connections=connections,
    )