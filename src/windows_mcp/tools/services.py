from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from ..models import ServiceStatus
from ..services.diagnostics import DiagnosticService


def register_service_tools(
    mcp: MCPServer,
    diagnostics: DiagnosticService,
) -> None:
    """
    Register read-only Windows service diagnostic tools.
    """

    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            open_world_hint=False,
        )
    )
    def get_service_status(
        target: str,
        service_name: str,
    ) -> ServiceStatus:
        """
        Get the status and startup type of a Windows service.

        Args:
            target: Logical Windows target name.
            service_name: Windows service name, for example W32Time.
        """
        return diagnostics.get_service_status(
            target=target,
            service_name=service_name,
        )