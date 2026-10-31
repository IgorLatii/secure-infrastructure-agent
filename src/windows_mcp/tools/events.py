from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..models import WindowsEvents
from ..services.diagnostics import DiagnosticService


WindowsLogName = Literal[
    "System",
    "Application",
    "Security",
]

WindowsEventLevel = Literal[
    "LogAlways",
    "Critical",
    "Error",
    "Warning",
    "Information",
    "Verbose",
]

EventId = Annotated[
    int,
    Field(gt=0),
]


def register_event_tools(
    mcp: MCPServer,
    diagnostics: DiagnosticService,
) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            open_world_hint=False,
        )
    )
    def get_windows_events(
        target: str,
        log_name: WindowsLogName,
        lookback_minutes: Annotated[
            int,
            Field(ge=1, le=10080),
        ],
        levels: Annotated[
            list[WindowsEventLevel] | None,
            Field(
                max_length=6,
                description=(
                        "Optional Windows event levels. "
                        "Security audit events such as 4624 commonly use LogAlways. "
                        "When filtering Security events by event ID, omit this parameter "
                        "unless a specific event level is required."
                ),
            ),
        ] = None,
        event_ids: Annotated[
            list[EventId] | None,
            Field(max_length=20),
        ] = None,
        provider_name: Annotated[
            str | None,
            Field(max_length=256),
        ] = None,
        max_events: Annotated[
            int,
            Field(ge=1, le=100),
        ] = 50,
    ) -> WindowsEvents:
        """
        Get recent Windows Event Log entries using bounded filters.

        Args:
            target: Logical Windows target name.
            log_name: Windows event log to query.
            lookback_minutes: How far back in time to search.
            levels: Optional event severity levels.
            event_ids: Optional Windows event IDs.
            provider_name: Optional Windows event provider name.
            max_events: Maximum number of events to return.
        """
        return diagnostics.get_windows_events(
            target=target,
            log_name=log_name,
            lookback_minutes=lookback_minutes,
            levels=levels,
            event_ids=event_ids,
            provider_name=provider_name,
            max_events=max_events,
        )