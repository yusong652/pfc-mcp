"""PFC task execution tool backed by pfc-bridge."""

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client, get_task_manager
from pfc_mcp.config import get_bridge_config
from pfc_mcp.utils import RunInBackground, ScriptPath, TaskDescription, TimeoutMs


def register(mcp: FastMCP) -> None:
    """Register pfc_execute_task tool."""

    @mcp.tool()
    async def pfc_execute_task(
        entry_script: ScriptPath,
        description: TaskDescription,
        timeout: TimeoutMs = None,
        run_in_background: RunInBackground = True,
    ) -> str:
        """Submit a PFC script task for asynchronous execution.

        This MCP tool is stateless and optimized for background execution.
        Use pfc_check_task_status to monitor progress.
        """
        if not run_in_background:
            return (
                "run_in_background=false is not supported in pfc-mcp phase2. "
                "Please run in background and use pfc_check_task_status for polling."
            )

        config = get_bridge_config()
        task_manager = get_task_manager()
        task_id = task_manager.create_task(
            source="agent",
            entry_script=entry_script,
            description=description,
        )

        client = await get_bridge_client()
        response = await client.execute_task(
            script_path=entry_script,
            description=description,
            task_id=task_id,
            session_id=config.default_session_id,
            timeout_ms=timeout,
            run_in_background=True,
            source="agent",
        )

        status = response.get("status", "unknown")
        message = response.get("message", "")
        data = response.get("data") or {}

        if status != "pending":
            task_manager.update_status(task_id, "failed")
            return (
                "Task submission failed\n"
                f"- task_id: {task_id}\n"
                f"- status: {status}\n"
                f"- message: {message or 'unknown error'}"
            )

        task_manager.update_status(task_id, "running")

        git_commit = data.get("git_commit")
        git_line = f"\n- git_commit: {git_commit[:8]}" if git_commit else ""
        return (
            "Task submitted\n"
            f"- task_id: {task_id}\n"
            "- status: pending\n"
            f"- entry_script: {entry_script}\n"
            f"- description: {description}"
            f"{git_line}\n"
            f"- message: {message or 'submitted'}\n\n"
            f'Next: call pfc_check_task_status(task_id="{task_id}")'
        )
