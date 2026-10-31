from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from ..models import TopProcesses
from ..services.diagnostics import DiagnosticService


def register_process_tools(
    mcp: MCPServer,
    diagnostics: DiagnosticService,
) -> None:
    """
    Register read-only Windows process diagnostic tools.
    """

    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            open_world_hint=False,
        )
    )
    def get_top_processes(target: str) -> TopProcesses:
        """
        Get top resource-consuming processes for a Windows target.
        """
        return diagnostics.get_top_processes(target)