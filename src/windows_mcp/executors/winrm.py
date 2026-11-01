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
    ScheduledTask,
    ScheduledTasks,
    ScheduledTaskAction,
    StartupEntry,
    StartupEntries,
    NetworkConnection,
    NetworkConnections,
    ProcessDetails,
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
            WindowsOperation.SCHEDULED_TASKS: self._get_scheduled_tasks,
            WindowsOperation.STARTUP_ENTRIES: self._get_startup_entries,
            WindowsOperation.NETWORK_CONNECTIONS: self._get_network_connections,
            WindowsOperation.PROCESS_DETAILS: self._get_process_details,
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

    def _get_scheduled_tasks(
            self,
            target: str,
            parameters: dict[str, Any] | None = None,
    ) -> ScheduledTasks:
        if parameters is None:
            raise ValueError(
                "SCHEDULED_TASKS requires parameters"
            )

        task_name = parameters.get("task_name")
        max_tasks = parameters.get("max_tasks", 50)

        if task_name is not None:
            if (
                    not isinstance(task_name, str)
                    or not task_name
                    or len(task_name) > 256
            ):
                raise ValueError(
                    "task_name must be a non-empty string "
                    "with at most 256 characters"
                )

        if (
                isinstance(max_tasks, bool)
                or not isinstance(max_tasks, int)
                or not 1 <= max_tasks <= 100
        ):
            raise ValueError(
                "max_tasks must be an integer between 1 and 100"
            )

        task_query = {
            "task_name": task_name,
            "max_tasks": max_tasks,
        }

        encoded_query = base64.b64encode(
            json.dumps(task_query).encode("utf-8")
        ).decode("ascii")

        script = rf"""
        $queryBytes = [Convert]::FromBase64String('{encoded_query}')
        $queryJson = [Text.Encoding]::UTF8.GetString($queryBytes)
        $query = $queryJson | ConvertFrom-Json

        $tasks = @(
            Get-ScheduledTask |
                Where-Object {{
                    $null -eq $query.task_name -or
                    $_.TaskName -eq [string]$query.task_name
                }} |
                Select-Object -First ([int]$query.max_tasks) |
                ForEach-Object {{
                    $task = $_

                    $actions = @(
                        $task.Actions |
                            ForEach-Object {{
                                @{{
                                    execute = [string]$_.Execute
                                    arguments = [string]$_.Arguments
                                }}
                            }}
                    )

                    @{{
                        task_name = [string]$task.TaskName
                        task_path = [string]$task.TaskPath
                        state = [string]$task.State
                        enabled = [bool]$task.Settings.Enabled
                        actions = $actions
                    }}
                }}
        )

        @{{
            tasks = $tasks
        }} | ConvertTo-Json -Depth 5 -Compress
        """

        raw_output = self._transport.run_powershell(
            target=target,
            script=script,
        )

        data = json.loads(raw_output)

        tasks = [
            ScheduledTask(
                task_name=item["task_name"],
                task_path=item["task_path"],
                state=item["state"],
                enabled=item["enabled"],
                actions=[
                    ScheduledTaskAction(
                        execute=action["execute"],
                        arguments=action["arguments"],
                    )
                    for action in item["actions"]
                ],
            )
            for item in data["tasks"]
        ]

        return ScheduledTasks(
            target=target,
            tasks=tasks,
        )

    def _get_startup_entries(
            self,
            target: str,
            parameters: dict[str, Any] | None = None,
    ) -> StartupEntries:
        if parameters is None:
            raise ValueError(
                "STARTUP_ENTRIES requires parameters"
            )

        max_entries = parameters.get("max_entries", 50)

        if (
                isinstance(max_entries, bool)
                or not isinstance(max_entries, int)
                or not 1 <= max_entries <= 100
        ):
            raise ValueError(
                "max_entries must be an integer between 1 and 100"
            )

        script = rf"""
        $entries = @()

        $machineLocations = @(
            @{{
                Path = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'
                Location = 'HKLM\Software\Microsoft\Windows\CurrentVersion\Run'
            }},
            @{{
                Path = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce'
                Location = 'HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce'
            }}
        )

        foreach ($location in $machineLocations) {{
            if (Test-Path -LiteralPath $location.Path) {{
                $key = Get-Item -LiteralPath $location.Path

                foreach ($name in $key.GetValueNames()) {{
                    $entries += @{{
                        name = [string]$name
                        command = [string]$key.GetValue(
                            $name,
                            $null,
                            [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames
                        )
                        location = [string]$location.Location
                        scope = 'Machine'
                        user_sid = $null
                    }}
                }}
            }}
        }}

        $userSids = @(
            Get-ChildItem -LiteralPath 'Registry::HKEY_USERS' |
                Where-Object {{
                    $_.PSChildName -match '^S-1-5-21-(\d+-){{3}}\d+$'
                }} |
                Select-Object -ExpandProperty PSChildName
        )

        foreach ($sid in $userSids) {{
            $userLocations = @(
                @{{
                    Path = "Registry::HKEY_USERS\$sid\Software\Microsoft\Windows\CurrentVersion\Run"
                    Location = "HKU\$sid\Software\Microsoft\Windows\CurrentVersion\Run"
                }},
                @{{
                    Path = "Registry::HKEY_USERS\$sid\Software\Microsoft\Windows\CurrentVersion\RunOnce"
                    Location = "HKU\$sid\Software\Microsoft\Windows\CurrentVersion\RunOnce"
                }}
            )

            foreach ($location in $userLocations) {{
                if (Test-Path -LiteralPath $location.Path) {{
                    $key = Get-Item -LiteralPath $location.Path

                    foreach ($name in $key.GetValueNames()) {{
                        $entries += @{{
                            name = [string]$name
                            command = [string]$key.GetValue(
                                $name,
                                $null,
                                [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames
                            )
                            location = [string]$location.Location
                            scope = 'User'
                            user_sid = [string]$sid
                        }}
                    }}
                }}
            }}
        }}

        @{{
            entries = @(
                $entries |
                    Select-Object -First {max_entries}
            )
        }} | ConvertTo-Json -Depth 4 -Compress
        """

        raw_output = self._transport.run_powershell(
            target=target,
            script=script,
        )

        data = json.loads(raw_output)

        entries = [
            StartupEntry(
                name=item["name"],
                command=item["command"],
                location=item["location"],
                scope=item["scope"],
                user_sid=item["user_sid"],
            )
            for item in data["entries"]
        ]

        return StartupEntries(
            target=target,
            entries=entries,
        )


    def _get_network_connections(
            self,
            target: str,
            parameters: dict[str, object] | None,
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

        raw_output = self._transport.run_powershell(
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

    def _get_process_details(
            self,
            target: str,
            parameters: dict[str, object] | None,
    ) -> ProcessDetails:
        if parameters is None or "pid" not in parameters:
            raise ValueError(
                "PROCESS_DETAILS requires parameter: pid"
            )

        pid = parameters["pid"]

        if isinstance(pid, bool) or not isinstance(pid, int):
            raise ValueError(
                "pid must be an integer"
            )

        if pid < 1:
            raise ValueError(
                "pid must be greater than 0"
            )

        script = f"""
        $process = Get-CimInstance Win32_Process `
            -Filter "ProcessId = {pid}" `
            -ErrorAction SilentlyContinue

        if ($null -eq $process) {{
            throw "Process not found"
        }}

        $runtimeProcess = Get-Process `
            -Id {pid} `
            -IncludeUserName `
            -ErrorAction SilentlyContinue

        $userName = $null
        $startTime = $null

        if ($null -ne $runtimeProcess) {{
            $userName = [string]$runtimeProcess.UserName

            try {{
                $startTime = $runtimeProcess.StartTime.ToUniversalTime().ToString('o')
            }}
            catch {{
                $startTime = $null
            }}
        }}

        $result = @{{
            pid = [int]$process.ProcessId
            name = [string]$process.Name
            executable_path = $process.ExecutablePath
            command_line = $process.CommandLine
            parent_pid = [int]$process.ParentProcessId
            user = $userName
            start_time = $startTime
        }}

        $result | ConvertTo-Json -Compress
        """

        raw_output = self._transport.run_powershell(
            target=target,
            script=script,
        )

        data = json.loads(raw_output)

        return ProcessDetails(
            target=target,
            pid=data["pid"],
            name=data["name"],
            executable_path=data["executable_path"],
            command_line=data["command_line"],
            parent_pid=data["parent_pid"],
            user=data["user"],
            start_time=data["start_time"],
        )