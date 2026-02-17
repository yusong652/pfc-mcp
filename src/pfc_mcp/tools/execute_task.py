"""PFC task execution tool backed by pfc-bridge."""

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
        """Submit a PFC script task for asynchronous execution.

        This MCP tool is stateless and optimized for background execution.
        Use pfc_check_task_status to monitor progress.
        """
        task_id = uuid.uuid4().hex[:6]

        try:
            client = await get_bridge_client()
            response = await client.execute_task(
                script_path=entry_script,
                description=description,
                task_id=task_id,
            )
        except Exception as exc:
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
