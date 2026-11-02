import json
from typing import Any

from ...models import ProcessInfo, TopProcesses
from ...transports.base import WindowsTransport


def get_top_processes(
        transport: WindowsTransport,
        target: str,
        parameters: dict[str, Any] | None = None,
) -> TopProcesses:
    script = r"""
    $logicalCpu = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors

    $processes = @(
        Get-CimInstance Win32_PerfFormattedData_PerfProc_Process |
            Where-Object {
                $_.IDProcess -gt 0 -and
                $_.Name -ne '_Total'
            } |
            ForEach-Object {
                $process = Get-Process -Id $_.IDProcess -ErrorAction SilentlyContinue

                if ($process) {
                    [PSCustomObject]@{
                        name = $process.ProcessName + '.exe'
                        pid = [int]$_.IDProcess
                        cpu_percent = [math]::Round(
                            [double]$_.PercentProcessorTime / $logicalCpu,
                            2
                        )
                        memory_mb = [math]::Round(
                            [double]$_.WorkingSetPrivate / 1MB,
                            2
                        )
                    }
                }
            }
    )

    $result = @{
        top_by_cpu = @(
            $processes |
                Sort-Object cpu_percent -Descending |
                Select-Object -First 5
        )
        top_by_memory = @(
            $processes |
                Sort-Object memory_mb -Descending |
                Select-Object -First 5
        )
    }

    $result | ConvertTo-Json -Depth 4 -Compress
    """

    raw_output = transport.run_powershell(
        target=target,
        script=script,
    )

    data = json.loads(raw_output)

    def parse_processes(
            items: list[dict[str, Any]],
    ) -> list[ProcessInfo]:
        return [
            ProcessInfo(
                name=process["name"],
                pid=process["pid"],
                cpu_percent=process["cpu_percent"],
                memory_mb=process["memory_mb"],
            )
            for process in items
        ]

    return TopProcesses(
        target=target,
        top_by_cpu=parse_processes(data["top_by_cpu"]),
        top_by_memory=parse_processes(data["top_by_memory"]),
    )