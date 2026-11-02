import base64
import json
from typing import Any

from ...models import WindowsEvent, WindowsEvents
from ...transports.base import WindowsTransport


def get_windows_events(
        transport: WindowsTransport,
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

    raw_output = transport.run_powershell(
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
