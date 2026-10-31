import json
from typing import Any

from .base import WindowsExecutor
from .operations import WindowsOperation
from ..models import (
    DiskInfo,
    MemoryInfo,
    ProcessInfo,
    SystemHealth,
    TopProcesses,
)
from ..transports.base import WindowsTransport


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
    ) -> Any:
        handlers = {
            WindowsOperation.SYSTEM_HEALTH: self._get_system_health,
            WindowsOperation.TOP_PROCESSES: self._get_top_processes,
        }

        try:
            handler = handlers[operation]
        except KeyError:
            raise ValueError(
                f"Unsupported operation: {operation}"
            ) from None

        return handler(target)

    def _get_system_health(self, target: str) -> SystemHealth:
        script = r"""
    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor
    $disks = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3"

    $totalMemory = [double]$os.TotalVisibleMemorySize
    $freeMemory = [double]$os.FreePhysicalMemory
    $usedMemory = $totalMemory - $freeMemory

    $pendingReboot = (
        (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') -or
        (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')
    )

    $result = [PSCustomObject]@{
        uptime_hours = [math]::Round(
            ((Get-Date) - $os.LastBootUpTime).TotalHours,
            2
        )
        cpu_percent = [math]::Round(
            (($cpu | Measure-Object -Property LoadPercentage -Average).Average),
            2
        )
        memory = @{
            total_gb = [math]::Round($totalMemory / 1MB, 2)
            used_gb = [math]::Round($usedMemory / 1MB, 2)
            used_percent = [math]::Round(
                ($usedMemory / $totalMemory) * 100,
                2
            )
        }
        disks = @(
            $disks | ForEach-Object {
                @{
                    drive = $_.DeviceID
                    total_gb = [math]::Round($_.Size / 1GB, 2)
                    free_gb = [math]::Round($_.FreeSpace / 1GB, 2)
                }
            }
        )
        pending_reboot = $pendingReboot
    }

    $result | ConvertTo-Json -Depth 4 -Compress
    """

        raw_output = self._transport.run_powershell(
            target=target,
            script=script,
        )

        data = json.loads(raw_output)

        return SystemHealth(
            target=target,
            uptime_hours=data["uptime_hours"],
            cpu_percent=data["cpu_percent"],
            memory=MemoryInfo(
                total_gb=data["memory"]["total_gb"],
                used_gb=data["memory"]["used_gb"],
                used_percent=data["memory"]["used_percent"],
            ),
            disks=[
                DiskInfo(
                    drive=disk["drive"],
                    total_gb=disk["total_gb"],
                    free_gb=disk["free_gb"],
                )
                for disk in data["disks"]
            ],
            pending_reboot=data["pending_reboot"],
        )

    def _get_top_processes(self, target: str) -> TopProcesses:
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

        raw_output = self._transport.run_powershell(
            target=target,
            script=script,
        )

        data = json.loads(raw_output)

        def parse_processes(items: list[dict[str, Any]]) -> list[ProcessInfo]:
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