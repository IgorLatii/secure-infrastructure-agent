import base64
import json
from typing import Any

from ...models import ServiceStatus
from ...transports.base import WindowsTransport


def get_service_status(
        transport: WindowsTransport,
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

    raw_output = transport.run_powershell(
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