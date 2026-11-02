import json
from typing import Any

from ...models import StartupEntry, StartupEntries
from ...transports.base import WindowsTransport


def get_startup_entries(
        transport: WindowsTransport,
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

    raw_output = transport.run_powershell(
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
