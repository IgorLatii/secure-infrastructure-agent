from mcp.server import MCPServer

from .executors.base import WindowsExecutor
from .executors.fake import FakeWindowsExecutor
from .services.diagnostics import DiagnosticService
from .tools.health import register_health_tools
from .tools.processes import register_process_tools
from .tools.services import register_service_tools
from .tools.events import register_event_tools
from .tools.tasks import register_task_tools
from .tools.startup import register_startup_tools
from .tools.network import register_network_tools
from .tools.process_details import register_process_detail_tools


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

    register_process_tools(
        mcp=mcp,
        diagnostics=diagnostics,
    )

    register_service_tools(
        mcp=mcp,
        diagnostics=diagnostics,
    )

    register_event_tools(
        mcp=mcp,
        diagnostics=diagnostics
    )

    register_task_tools(
        mcp=mcp,
        diagnostics=diagnostics,
    )

    register_startup_tools(
        mcp=mcp,
        diagnostics=diagnostics,
    )

    register_network_tools(
        mcp=mcp,
        diagnostics=diagnostics,
    )

    register_process_detail_tools(
        mcp=mcp,
        diagnostics=diagnostics,
    )

    return mcp