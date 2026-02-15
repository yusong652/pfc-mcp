"""Task listing tool backed by pfc-bridge."""

from typing import Optional
from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.contracts import build_error_from_legacy, build_ok
from pfc_mcp.formatting import format_bridge_unavailable, format_operation_error, format_unix_timestamp, normalize_status
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
            return build_error_from_legacy(format_bridge_unavailable("pfc_list_tasks", exc))

        status = response.get("status", "unknown")
        if status != "success":
            return build_error_from_legacy(
                format_operation_error(
                    "pfc_list_tasks",
                    status=status or "list_failed",
                    message=response.get("message", "Failed to list tasks"),
                    action="Check bridge state and retry",
                )
            )

        tasks = response.get("data") or []
        pagination = response.get("pagination") or {}
        total_count = pagination.get("total_count", len(tasks))
        displayed_count = pagination.get("displayed_count", len(tasks))
        has_more = pagination.get("has_more", False)

        normalized_tasks: list[dict[str, Any]] = []

        for task in tasks:
            normalized_task = {
                "task_id": task.get("task_id"),
                "status": normalize_status(task.get("status", "unknown")),
                "source": task.get("source", "agent"),
                "start_time": format_unix_timestamp(task.get("start_time")),
                "end_time": format_unix_timestamp(task.get("end_time")),
                "elapsed_time": task.get("elapsed_time"),
                "entry_script": task.get("entry_script") or task.get("name"),
                "description": task.get("description"),
            }
            normalized_tasks.append(normalized_task)

        return build_ok(
            {
                "total_count": total_count,
                "displayed_count": displayed_count,
                "has_more": has_more,
                "tasks": normalized_tasks,
            }
        )
