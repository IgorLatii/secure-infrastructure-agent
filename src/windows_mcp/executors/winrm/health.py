import json
from typing import Any

from ...models import DiskInfo, MemoryInfo, SystemHealth
from ...transports.base import WindowsTransport


def get_system_health(
        transport: WindowsTransport,
        target: str,
        parameters: dict[str, Any] | None = None,
) -> SystemHealth:
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

    raw_output = transport.run_powershell(
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
