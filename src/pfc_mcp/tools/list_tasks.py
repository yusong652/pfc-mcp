"""Task listing tool backed by pfc-bridge."""

from typing import Optional
from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.formatting import format_bridge_unavailable, format_operation_error, normalize_status
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
    ) -> dict[str, Any]:
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
            return {
                "operation": "pfc_list_tasks",
                "status": "success",
                "total_count": 0,
                "displayed_count": 0,
                "skip_newest": skip_newest,
                "limit": limit,
                "has_more": False,
                "session_filter": session_id,
                "tasks": [],
                "display": "No tracked tasks found.",
            }

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

        normalized_tasks: list[dict[str, Any]] = []

        for task in tasks:
            raw_status = task.get("status", "unknown")
            checked = task.get("checked")
            if checked is None and "notified" in task:
                checked = task.get("notified")

            normalized_task = {
                "task_id": task.get("task_id"),
                "status": normalize_status(raw_status),
                "source": task.get("source", "agent"),
                "elapsed_time": task.get("elapsed_time"),
                "checked": checked,
                "entry_script": task.get("entry_script") or task.get("name"),
                "description": task.get("description"),
            }
            normalized_tasks.append(normalized_task)

            lines.append(
                (
                    f"- task_id={normalized_task.get('task_id', 'unknown')} "
                    f"status={normalized_task.get('status', 'unknown')} "
                    f"source={normalized_task.get('source', 'agent')} "
                    f"elapsed={normalized_task.get('elapsed_time', 'n/a')} "
                    f"checked={checked if checked is not None else 'n/a'}"
                )
            )
            lines.append(f"  entry_script={normalized_task.get('entry_script') or 'n/a'}")
            lines.append(f"  description={normalized_task.get('description') or 'n/a'}")

        if has_more:
            lines.extend(["", f"Next: pfc_list_tasks(skip_newest={skip_newest + displayed_count}, limit={limit})"])

        return {
            "operation": "pfc_list_tasks",
            "status": "success",
            "total_count": total_count,
            "displayed_count": displayed_count,
            "skip_newest": skip_newest,
            "limit": limit,
            "has_more": has_more,
            "session_filter": session_id,
            "tasks": normalized_tasks,
            "display": "\n".join(lines),
        }
