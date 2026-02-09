"""PFC task execution tool backed by pfc-bridge."""

from typing import Any

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client, get_task_manager
from pfc_mcp.config import get_bridge_config
from pfc_mcp.tools.error_messages import format_bridge_unavailable, format_operation_error
from pfc_mcp.utils import ScriptPath, TaskDescription, TimeoutSeconds


def register(mcp: FastMCP) -> None:
    """Register pfc_execute_task tool."""

    @mcp.tool()
    async def pfc_execute_task(
        entry_script: ScriptPath,
        description: TaskDescription,
        timeout: TimeoutSeconds = None,
    ) -> dict[str, Any]:
        """Submit a PFC script task for asynchronous execution.

        This MCP tool is stateless and optimized for background execution.
        Use pfc_check_task_status to monitor progress.
        """
        config = get_bridge_config()
        task_manager = get_task_manager()
        task_id = task_manager.create_task(
            entry_script=entry_script,
            description=description,
        )

        try:
            client = await get_bridge_client()
            response = await client.execute_task(
                script_path=entry_script,
                description=description,
                task_id=task_id,
                session_id=config.default_session_id,
                timeout_ms=int(timeout * 1000) if timeout else None,
                run_in_background=True,
            )
        except Exception as exc:
            task_manager.update_status(task_id, "failed")
            return format_bridge_unavailable("pfc_execute_task", exc, task_id=task_id)

        status = response.get("status", "unknown")
        message = response.get("message", "")
        data = response.get("data") or {}

        if status != "pending":
            task_manager.update_status(task_id, "failed")
            return format_operation_error(
                "pfc_execute_task",
                status=status or "submission_failed",
                message=message or "Task submission rejected by bridge",
                task_id=task_id,
                action="Check script path and bridge logs, then retry",
            )

        task_manager.update_status(task_id, "running")

        display = (
            "Task submitted\n"
            f"- task_id: {task_id}\n"
            "- status: pending\n"
            f"- entry_script: {entry_script}\n"
            f"- description: {description}\n"
            f"- message: {message or 'submitted'}\n\n"
            f'Next: call pfc_check_task_status(task_id="{task_id}")'
        )

        return {
            "operation": "pfc_execute_task",
            "status": "pending",
            "task_id": task_id,
            "entry_script": entry_script,
            "description": description,
            "message": message or "submitted",
            "display": display,
        }
