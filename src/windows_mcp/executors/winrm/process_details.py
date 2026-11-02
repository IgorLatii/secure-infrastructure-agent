import json
from typing import Any

from ...models import ProcessDetails
from ...transports.base import WindowsTransport


def get_process_details(
        transport: WindowsTransport,
        target: str,
        parameters: dict[str, Any] | None,
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

    raw_output = transport.run_powershell(
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
