"""Task listing tool backed by pfc-bridge."""

from typing import Optional

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.tools.error_messages import format_bridge_unavailable, format_operation_error
from pfc_mcp.tools.task_formatting import normalize_status
from pfc_mcp.utils import SkipNewestTasks, TaskListLimit


def register(mcp: FastMCP) -> None:
    """Register pfc_list_tasks tool."""

    @mcp.tool()
    async def pfc_list_tasks(
        session_id: Optional[str] = Field(
            default=None,
            description="Optional session filter. Omit to list all sessions.",
        ),
        skip_newest: SkipNewestTasks = 0,
        limit: TaskListLimit = 32,
    ) -> str | dict[str, str]:
        """List tracked PFC tasks with pagination."""
        try:
            client = await get_bridge_client()
            response = await client.list_tasks(
                session_id=session_id,
                offset=skip_newest,
                limit=limit,
            )
        except Exception as exc:
            return format_bridge_unavailable("pfc_list_tasks", exc)

        status = response.get("status", "unknown")
        if status != "success":
            return format_operation_error(
                "pfc_list_tasks",
                status=status or "list_failed",
                message=response.get("message", "Failed to list tasks"),
                action="Check bridge state and retry",
            )

        tasks = response.get("data") or []
        pagination = response.get("pagination") or {}
        total_count = pagination.get("total_count", len(tasks))
        displayed_count = pagination.get("displayed_count", len(tasks))
        has_more = pagination.get("has_more", False)

        if total_count == 0:
            return "No tracked tasks found."

        lines = [
            "Tracked tasks",
            f"- total_count: {total_count}",
            f"- displayed_count: {displayed_count}",
            f"- skip_newest: {skip_newest}",
            f"- limit: {limit}",
            f"- has_more: {has_more}",
            f"- session_filter: {session_id or 'none'}",
            "",
        ]

        for task in tasks:
            raw_status = task.get("status", "unknown")
            checked = task.get("checked")
            if checked is None and "notified" in task:
                checked = task.get("notified")

            lines.append(
                (
                    f"- task_id={task.get('task_id', 'unknown')} "
                    f"status={normalize_status(raw_status)} "
                    f"source={task.get('source', 'agent')} "
                    f"elapsed={task.get('elapsed_time', 'n/a')} "
                    f"checked={checked if checked is not None else 'n/a'}"
                )
            )
            lines.append(f"  entry_script={task.get('entry_script') or task.get('name') or 'n/a'}")
            lines.append(f"  description={task.get('description') or 'n/a'}")

        if has_more:
            lines.extend(["", f"Next: pfc_list_tasks(skip_newest={skip_newest + displayed_count}, limit={limit})"])

        return "\n".join(lines)
