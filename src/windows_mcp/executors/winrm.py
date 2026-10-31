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
    WindowsEvent,
    WindowsEvents,
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
            WindowsOperation.WINDOWS_EVENTS: self._get_windows_events,
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

    def _get_windows_events(
            self,
            target: str,
            parameters: dict[str, Any] | None = None,
    ) -> WindowsEvents:
        if parameters is None:
            raise ValueError(
                "WINDOWS_EVENTS requires parameters"
            )

        log_name = parameters.get("log_name")
        lookback_minutes = parameters.get("lookback_minutes")
        levels = parameters.get("levels")
        event_ids = parameters.get("event_ids")
        provider_name = parameters.get("provider_name")
        max_events = parameters.get("max_events", 50)

        allowed_logs = {
            "System",
            "Application",
            "Security",
        }

        allowed_levels = {
            "LogAlways",
            "Critical",
            "Error",
            "Warning",
            "Information",
            "Verbose",
        }

        if log_name not in allowed_logs:
            raise ValueError(
                "log_name must be one of: "
                "System, Application, Security"
            )

        if (
                isinstance(lookback_minutes, bool)
                or not isinstance(lookback_minutes, int)
                or not 1 <= lookback_minutes <= 10080
        ):
            raise ValueError(
                "lookback_minutes must be an integer between 1 and 10080"
            )

        if (
                isinstance(max_events, bool)
                or not isinstance(max_events, int)
                or not 1 <= max_events <= 100
        ):
            raise ValueError(
                "max_events must be an integer between 1 and 100"
            )

        if levels is not None:
            if (
                    not isinstance(levels, list)
                    or not 1 <= len(levels) <= 6
                    or any(level not in allowed_levels for level in levels)
            ):
                raise ValueError(
                    "levels contains invalid Windows event levels"
                )

        if event_ids is not None:
            if (
                    not isinstance(event_ids, list)
                    or not 1 <= len(event_ids) <= 20
                    or any(
                isinstance(event_id, bool)
                or not isinstance(event_id, int)
                or event_id <= 0
                for event_id in event_ids
            )
            ):
                raise ValueError(
                    "event_ids must contain 1 to 20 positive integers"
                )

        if provider_name is not None:
            if (
                    not isinstance(provider_name, str)
                    or not provider_name
                    or len(provider_name) > 256
            ):
                raise ValueError(
                    "provider_name must be a non-empty string "
                    "with at most 256 characters"
                )

        event_query = {
            "log_name": log_name,
            "lookback_minutes": lookback_minutes,
            "levels": levels,
            "event_ids": event_ids,
            "provider_name": provider_name,
            "max_events": max_events,
        }

        encoded_query = base64.b64encode(
            json.dumps(event_query).encode("utf-8")
        ).decode("ascii")

        script = rf"""
        $queryBytes = [Convert]::FromBase64String('{encoded_query}')
        $queryJson = [Text.Encoding]::UTF8.GetString($queryBytes)
        $query = $queryJson | ConvertFrom-Json

        $levelMap = @{{
            'LogAlways' = 0
            'Critical' = 1
            'Error' = 2
            'Warning' = 3
            'Information' = 4
            'Verbose' = 5
        }}

        $levelNameMap = @{{
            0 = 'LogAlways'
            1 = 'Critical'
            2 = 'Error'
            3 = 'Warning'
            4 = 'Information'
            5 = 'Verbose'
        }}

        $filter = @{{
            LogName = [string]$query.log_name
            StartTime = (Get-Date).AddMinutes(
                -[int]$query.lookback_minutes
            )
        }}

        if ($null -ne $query.levels) {{
            $filter.Level = @(
                $query.levels | ForEach-Object {{
                    $levelMap[[string]$_]
                }}
            )
        }}

        if ($null -ne $query.event_ids) {{
            $filter.Id = @(
                $query.event_ids | ForEach-Object {{
                    [int]$_
                }}
            )
        }}

        if ($null -ne $query.provider_name) {{
            $filter.ProviderName = [string]$query.provider_name
        }}

        try {{
            $rawEvents = @(
                Get-WinEvent -FilterHashtable $filter -ErrorAction Stop |
                Select-Object -First ([int]$query.max_events)
            )
        }}
        catch {{
            if (
                $_.FullyQualifiedErrorId -like
                'NoMatchingEventsFound,Microsoft.PowerShell.Commands.GetWinEventCommand*'
            ) {{
                $rawEvents = @()
            }}
            else {{
                throw
            }}
        }}

        $events = @(
            $rawEvents |
                ForEach-Object {{
                    $message = [string]$_.Message
                    $messageTruncated = $false

                    if ($message.Length -gt 3000) {{
                        $message = $message.Substring(0, 3000)
                        $messageTruncated = $true
                    }}

                    @{{
                        event_id = [int]$_.Id
                        provider_name = [string]$_.ProviderName
                        level = [string]$levelNameMap[[int]$_.Level]
                        time_created = $_.TimeCreated.ToUniversalTime().ToString('o')
                        record_id = [long]$_.RecordId
                        message = $message
                        message_truncated = $messageTruncated
                    }}
                }}
        )

        @{{
            events = $events
        }} | ConvertTo-Json -Depth 4 -Compress
        """

        raw_output = self._transport.run_powershell(
            target=target,
            script=script,
        )

        data = json.loads(raw_output)

        return WindowsEvents(
            target=target,
            log_name=log_name,
            lookback_minutes=lookback_minutes,
            events=[
                WindowsEvent(
                    event_id=event["event_id"],
                    provider_name=event["provider_name"],
                    level=event["level"],
                    time_created=event["time_created"],
                    record_id=event["record_id"],
                    message=event["message"],
                    message_truncated=event["message_truncated"],
                )
                for event in data["events"]
            ],
        )