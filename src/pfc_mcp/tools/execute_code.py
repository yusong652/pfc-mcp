"""PFC user console execution tool backed by pfc-bridge."""

import os

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.bridge import get_bridge_client, get_task_manager
from pfc_mcp.config import get_bridge_config
from pfc_mcp.tools.error_messages import format_bridge_unavailable
from pfc_mcp.tools.task_formatting import format_unix_timestamp, normalize_status
from pfc_mcp.utils import ConsoleCode, ConsoleTimeoutSeconds


def register(mcp: FastMCP) -> None:
    """Register pfc_execute_code tool."""

    @mcp.tool()
    async def pfc_execute_code(
        code: ConsoleCode,
        timeout: ConsoleTimeoutSeconds = 30,
        run_in_background: bool = Field(
            default=False,
            description="When true, return task_id immediately and poll with pfc_check_task_status.",
        ),
    ) -> str | dict[str, str]:
        """Execute Python code in the PFC user console environment."""
        config = get_bridge_config()
        task_manager = get_task_manager()
        task_id = task_manager.create_task(
            entry_script="<user_console>",
            description=code.splitlines()[0][:120],
        )

        try:
            client = await get_bridge_client()

            workspace_path = config.workspace_path
            if not workspace_path:
                workspace_path = await client.get_working_directory()
            if not workspace_path:
                workspace_path = os.getcwd()

            response = await client.execute_code(
                code=code,
                workspace_path=workspace_path,
                task_id=task_id,
                session_id=config.default_session_id,
                timeout_ms=int(timeout * 1000),
                run_in_background=run_in_background,
            )
        except Exception as exc:
            task_manager.update_status(task_id, "failed")
            return format_bridge_unavailable("pfc_execute_code", exc, task_id=task_id)

        status = response.get("status", "unknown")
        message = response.get("message", "")
        data = response.get("data") or {}
        normalized_status = normalize_status(status)

        if status == "pending":
            task_manager.update_status(task_id, "running")
            return (
                "Console task submitted\n"
                f"- task_id: {task_id}\n"
                "- status: pending\n"
                f"- workspace_path: {workspace_path}\n"
                f"- message: {message or 'submitted'}\n\n"
                f'Next: call pfc_check_task_status(task_id="{task_id}")'
            )

        if normalized_status in {"completed", "failed", "interrupted"}:
            task_manager.update_status(task_id, normalized_status)
        else:
            task_manager.update_status(task_id, "failed")

        output = data.get("output") or "(no output)"
        result_value = data.get("result")
        error_text = data.get("error")
        start_time = format_unix_timestamp(data.get("start_time"))
        end_time = format_unix_timestamp(data.get("end_time"))

        lines = [
            "Console execution result",
            f"- task_id: {task_id}",
            f"- status: {normalized_status}",
            f"- workspace_path: {workspace_path}",
            f"- start_time: {start_time}",
            f"- end_time: {end_time}",
            f"- message: {message or 'n/a'}",
        ]

        if result_value is not None:
            lines.append(f"- result: {result_value}")
        if error_text:
            lines.append(f"- error: {error_text}")

        lines.extend(["", "Output:", output])
        return "\n".join(lines)
