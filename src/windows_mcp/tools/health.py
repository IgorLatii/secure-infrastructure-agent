from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from ..models import SystemHealth
from ..services.diagnostics import DiagnosticService


def register_health_tools(
    mcp: MCPServer,
    diagnostics: DiagnosticService,
) -> None:
    """
    Register read-only Windows health diagnostic tools.
    """

    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            open_world_hint=False,
        )
    )
    def get_system_health(target: str) -> SystemHealth:
        """
        Get a read-only system health snapshot for a Windows target.
        """
        return diagnostics.get_system_health(target)