import base64
import json
from typing import Any

from ...models import (
    ScheduledTask,
    ScheduledTaskAction,
    ScheduledTasks,
)
from ...transports.base import WindowsTransport


def get_scheduled_tasks(
        transport: WindowsTransport,
        target: str,
        parameters: dict[str, Any] | None = None,
) -> ScheduledTasks:
    if parameters is None:
        raise ValueError(
            "SCHEDULED_TASKS requires parameters"
        )

    task_name = parameters.get("task_name")
    max_tasks = parameters.get("max_tasks", 50)

    if task_name is not None:
        if (
                not isinstance(task_name, str)
                or not task_name
                or len(task_name) > 256
        ):
            raise ValueError(
                "task_name must be a non-empty string "
                "with at most 256 characters"
            )

    if (
            isinstance(max_tasks, bool)
            or not isinstance(max_tasks, int)
            or not 1 <= max_tasks <= 100
    ):
        raise ValueError(
            "max_tasks must be an integer between 1 and 100"
        )

    task_query = {
        "task_name": task_name,
        "max_tasks": max_tasks,
    }

    encoded_query = base64.b64encode(
        json.dumps(task_query).encode("utf-8")
    ).decode("ascii")

    script = rf"""
    $queryBytes = [Convert]::FromBase64String('{encoded_query}')
    $queryJson = [Text.Encoding]::UTF8.GetString($queryBytes)
    $query = $queryJson | ConvertFrom-Json

    $tasks = @(
        Get-ScheduledTask |
            Where-Object {{
                $null -eq $query.task_name -or
                $_.TaskName -eq [string]$query.task_name
            }} |
            Select-Object -First ([int]$query.max_tasks) |
            ForEach-Object {{
                $task = $_

                $actions = @(
                    $task.Actions |
                        ForEach-Object {{
                            @{{
                                execute = [string]$_.Execute
                                arguments = [string]$_.Arguments
                            }}
                        }}
                )

                @{{
                    task_name = [string]$task.TaskName
                    task_path = [string]$task.TaskPath
                    state = [string]$task.State
                    enabled = [bool]$task.Settings.Enabled
                    actions = $actions
                }}
            }}
    )

    @{{
        tasks = $tasks
    }} | ConvertTo-Json -Depth 5 -Compress
    """

    raw_output = transport.run_powershell(
        target=target,
        script=script,
    )

    data = json.loads(raw_output)

    tasks = [
        ScheduledTask(
            task_name=item["task_name"],
            task_path=item["task_path"],
            state=item["state"],
            enabled=item["enabled"],
            actions=[
                ScheduledTaskAction(
                    execute=action["execute"],
                    arguments=action["arguments"],
                )
                for action in item["actions"]
            ],
        )
        for item in data["tasks"]
    ]

    return ScheduledTasks(
        target=target,
        tasks=tasks,
    )
