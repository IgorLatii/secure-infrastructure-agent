from typing import Annotated

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..models import ProcessDetails
from ..services.diagnostics import DiagnosticService


def register_process_detail_tools(
        mcp: MCPServer,
        diagnostics: DiagnosticService,
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            openWorldHint=False,
        )
    )
    def get_process_details(
            target: str,
            pid: Annotated[
                int,
                Field(
                    ge=1,
                    description="Process ID to inspect.",
                ),
            ],
    ) -> ProcessDetails:
        """
        Inspect detailed information about a specific Windows process.

        Returns structured process evidence including executable path,
        command line, parent process ID, user, and start time.

        Use this tool during endpoint security investigation to examine
        a process identified by another diagnostic source such as a
        network connection or security alert.
        """
        return diagnostics.get_process_details(
            target=target,
            pid=pid,
        )