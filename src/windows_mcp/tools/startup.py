from typing import Annotated

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..models import StartupEntries
from ..services.diagnostics import DiagnosticService


def register_startup_tools(
    mcp: MCPServer,
    diagnostics: DiagnosticService,
) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            open_world_hint=False,
        )
    )
    def get_startup_entries(
        target: str,
        max_entries: Annotated[
            int,
            Field(
                ge=1,
                le=100,
                description=(
                    "Maximum number of Windows startup persistence "
                    "entries to return."
                ),
            ),
        ] = 50,
    ) -> StartupEntries:
        """
        Get Windows startup persistence entries as bounded read-only evidence.

        Use this tool to inspect common Windows autorun locations,
        such as Run and RunOnce registry keys, when investigating
        possible persistence.

        Args:
            target: Logical Windows target name.
            max_entries: Maximum number of startup entries to return.
        """
        return diagnostics.get_startup_entries(
            target=target,
            max_entries=max_entries,
        )