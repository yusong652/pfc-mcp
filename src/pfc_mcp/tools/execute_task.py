"""PFC task execution tool backed by itasca-mcp-bridge."""

import uuid
from typing import Any

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.contracts import build_ok
from pfc_mcp.formatting import build_bridge_error, build_operation_error
from pfc_mcp.utils import ScriptPath, TaskDescription


def register(mcp: FastMCP) -> None:
    """Register pfc_execute_task tool."""

    @mcp.tool()
    async def pfc_execute_task(
        entry_script: ScriptPath,
        description: TaskDescription,
    ) -> dict[str, Any]:
        """Submit a Python script file for asynchronous execution in PFC.

        Returns a task_id immediately; the script runs in the background.
        Use the companion tools to manage the task lifecycle:
        - pfc_check_task_status: poll output, progress, and final status
        - pfc_interrupt_task: cancel a running task
        - pfc_list_tasks: browse task history

        While the task is cycling, you can call pfc_execute_code at any
        time to inspect or modify simulation state — including variables
        the task depends on. This is the standard way to probe progress,
        tune parameters mid-run, swap callbacks, or trigger early
        termination via a sentinel variable. Both tools share the same
        __main__ namespace in PFC's main thread.

        Console output from itasca.command() inside the script —
        table dumps, list output, command summaries — is captured
        and interleaved with Python prints in the task log, visible
        through pfc_check_task_status.

        Do NOT have the script invoke `program call '<file>.p3dat'`
        (or .p2dat / .dat). PFC's command-script interpreter blocks
        the bridge for the script's entire duration with no cycle-gap
        interleaving, leaving the bridge unreachable until PFC is
        stopped manually. If the user asks to run a .dat / .p3dat /
        .p2dat file, read the file and translate its commands into a
        sequence of `itasca.command(...)` calls in the Python script
        instead.

        This is the async / background execution path: pollable via
        pfc_check_task_status, cancellable via pfc_interrupt_task.
        Submission does not lock parameters — start with reasonable
        values and refine live via pfc_execute_code as the task
        cycles. For synchronous, inline execution, use
        pfc_execute_code directly.
        """
        try:
            client = await get_bridge_client()
        except Exception as exc:
            # Connection failed — no task_id generated, nothing to track
            return build_bridge_error(exc)

        task_id = uuid.uuid4().hex[:6]

        try:
            response = await client.execute_task(
                script_path=entry_script,
                description=description,
                task_id=task_id,
            )
        except Exception as exc:
            # Connected but request failed — task may or may not exist on bridge
            return build_bridge_error(exc, task_id=task_id)

        status = response.get("status", "unknown")
        message = response.get("message", "")

        if status != "pending":
            return build_operation_error(
                status or "submission_failed",
                message or "Task submission rejected by bridge",
                task_id=task_id,
                action="Check script path and bridge logs, then retry",
            )

        return build_ok(
            {
                "task_id": task_id,
                "entry_script": entry_script,
                "description": description,
                "task_status": "pending",
                "message": message or "submitted",
            }
        )
