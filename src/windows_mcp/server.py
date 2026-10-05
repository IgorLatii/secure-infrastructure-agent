from mcp.server import MCPServer

from .executors.base import WindowsExecutor
from .executors.fake import FakeWindowsExecutor
from .services.diagnostics import DiagnosticService
from .tools.health import register_health_tools


def create_server(
    executor: WindowsExecutor | None = None,
) -> MCPServer:
    """
    Build and configure the Windows diagnostics MCP server.

    Uses the fake executor by default unless another
    Windows executor is explicitly provided.
    """
    if executor is None:
        executor = FakeWindowsExecutor()

    diagnostics = DiagnosticService(executor)

    mcp = MCPServer(
        name="windows-diagnostics",
    )

    register_health_tools(
        mcp=mcp,
        diagnostics=diagnostics,
    )

    return mcp