import json
from typing import Any
import base64

from .base import WindowsExecutor
from .operations import WindowsOperation
from ..models import (
    DiskInfo,
    MemoryInfo,
    ProcessInfo,
    ServiceStatus,
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
            parameters: dict[str, Any] | None = None,
    ) -> Any:
        handlers = {
            WindowsOperation.SYSTEM_HEALTH: self._get_system_health,
            WindowsOperation.TOP_PROCESSES: self._get_top_processes,
            WindowsOperation.SERVICE_STATUS: self._get_service_status,
        }

        try:
            handler = handlers[operation]
        except KeyError:
            raise ValueError(
                f"Unsupported operation: {operation}"
            ) from None

        return handler(target, parameters)

    def _get_system_health(
            self,
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

    def _get_top_processes(
            self,
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

    def _get_service_status(
            self,
            target: str,
            parameters: dict[str, Any] | None = None,
    ) -> ServiceStatus:
        if parameters is None or "service_name" not in parameters:
            raise ValueError(
                "SERVICE_STATUS requires parameter: service_name"
            )

        service_name = parameters["service_name"]

        if not isinstance(service_name, str) or not service_name:
            raise ValueError(
                "service_name must be a non-empty string"
            )

        encoded_service_name = base64.b64encode(
            service_name.encode("utf-8")
        ).decode("ascii")

        script = rf"""
        $serviceNameBytes = [Convert]::FromBase64String('{encoded_service_name}')
        $serviceName = [Text.Encoding]::UTF8.GetString($serviceNameBytes)

        $service = Get-CimInstance Win32_Service |
            Where-Object {{ $_.Name -eq $serviceName }}
    
        if ($null -eq $service) {{
            throw "Service not found"
        }}

        $result = @{{
            service_name = $service.Name
            display_name = $service.DisplayName
            status = $service.State
            start_type = $service.StartMode
        }}

        $result | ConvertTo-Json -Compress
        """

        raw_output = self._transport.run_powershell(
            target=target,
            script=script,
        )

        data = json.loads(raw_output)

        return ServiceStatus(
            target=target,
            service_name=data["service_name"],
            display_name=data["display_name"],
            status=data["status"],
            start_type=data["start_type"],
        )