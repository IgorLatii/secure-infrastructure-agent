from mcp.server import MCPServer

from .executors.fake import FakeWindowsExecutor
from .services.diagnostics import DiagnosticService
from .tools.health import register_health_tools


def create_server() -> MCPServer:
    """
    Build and configure the Windows diagnostics MCP server.
    """

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