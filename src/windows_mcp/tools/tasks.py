from typing import Annotated

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from ..models import ScheduledTasks
from ..services.diagnostics import DiagnosticService


def register_task_tools(
    mcp: MCPServer,
    diagnostics: DiagnosticService,
) -> None:

    @mcp.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            open_world_hint=False,
        )
    )
    def get_scheduled_tasks(
        target: str,
        task_name: Annotated[
            str | None,
            Field(
                min_length=1,
                max_length=256,
                description=(
                    "Optional scheduled task name to filter by. "
                    "Omit to inspect scheduled tasks on the target."
                ),
            ),
        ] = None,
        max_tasks: Annotated[
            int,
            Field(ge=1, le=100),
        ] = 50,
    ) -> ScheduledTasks:
        """
        Get Windows scheduled tasks as bounded read-only evidence.

        Args:
            target: Logical Windows target name.
            task_name: Optional scheduled task name to filter by.
            max_tasks: Maximum number of tasks to return.
        """
        return diagnostics.get_scheduled_tasks(
            target=target,
            task_name=task_name,
            max_tasks=max_tasks,
        )