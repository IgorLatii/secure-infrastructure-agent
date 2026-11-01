from typing import Annotated

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..models import NetworkConnections
from ..services.diagnostics import DiagnosticService

def register_network_tools(
        mcp: MCPServer,
        diagnostics: DiagnosticService,
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            openWorldHint=False,
        )
    )
    def get_network_connections(
            target: str,
            max_connections: Annotated[
                int,
                Field(
                    ge=1,
                    le=100,
                    description="Maximum number of TCP connections to return.",
                ),
            ] = 50,
    ) -> NetworkConnections:
        """
        Inspect TCP network connections on a Windows target.

        Returns structured connection evidence including local and remote
        endpoints, TCP state, owning process ID, and process name.

        Use this tool during endpoint security investigation to identify
        network activity associated with running processes.
        """
        return diagnostics.get_network_connections(
            target=target,
            max_connections=max_connections,
        )