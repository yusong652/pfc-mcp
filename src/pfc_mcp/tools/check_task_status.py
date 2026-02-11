"""Task status query tool backed by pfc-bridge."""

import asyncio
from typing import Any

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client, get_task_manager
from pfc_mcp.formatting import (
    format_bridge_unavailable,
    format_operation_error,
    format_unix_timestamp,
    normalize_status,
    paginate_output,
)
from pfc_mcp.utils import FilterText, OutputLimit, SkipNewestLines, TaskId, WaitSeconds


def register(mcp: FastMCP) -> None:
    """Register pfc_check_task_status tool."""

    @mcp.tool()
    async def pfc_check_task_status(
        task_id: TaskId,
        skip_newest: SkipNewestLines = 0,
        limit: OutputLimit = 64,
        filter: FilterText = None,
        wait_seconds: WaitSeconds = 1,
    ) -> dict[str, Any]:
        """Check status and output for a submitted PFC task."""
        await asyncio.sleep(wait_seconds)

        try:
            client = await get_bridge_client()
            response = await client.check_task_status(task_id)
        except Exception as exc:
            return format_bridge_unavailable("pfc_check_task_status", exc, task_id=task_id)

        status = response.get("status", "unknown")
        if status == "not_found":
            return format_operation_error(
                "pfc_check_task_status",
                status="not_found",
                message="Task not found",
                task_id=task_id,
                action="Verify task_id or submit a new task",
            )

        data = response.get("data") or {}
        normalized_status = normalize_status(status)

        output_text, pagination = paginate_output(
            output=data.get("output") or "",
            skip_newest=skip_newest,
            limit=limit,
            filter_text=filter,
        )

        checked = data.get("checked")
        if checked is None and "notified" in data:
            checked = data.get("notified")

        get_task_manager().update_status(task_id, normalized_status)

        lines = [
            "Task status",
            f"- task_id: {task_id}",
            f"- status: {normalized_status}",
            f"- start_time: {format_unix_timestamp(data.get('start_time'))}",
            f"- end_time: {format_unix_timestamp(data.get('end_time'))}",
            f"- elapsed_time: {data.get('elapsed_time', 'n/a')}",
            f"- entry_script: {data.get('entry_script') or data.get('script_path') or 'n/a'}",
            f"- description: {data.get('description') or 'n/a'}",
            f"- checked: {checked if checked is not None else 'n/a'}",
        ]

        if data.get("result") is not None:
            lines.append(f"- result: {data.get('result')}")
        if data.get("error"):
            lines.append(f"- error: {data.get('error')}")

        lines.extend(
            [
                "",
                (
                    "Output "
                    f"({pagination['total_lines']} lines, showing {pagination['line_range']}, "
                    f"has_newer={pagination['has_newer']}, has_older={pagination['has_older']}):"
                ),
                output_text,
            ]
        )

        next_hints = []
        if pagination["has_newer"]:
            next_hints.append(f"newer: skip_newest={max(0, skip_newest - limit)}")
        if pagination["has_older"]:
            next_hints.append(f"older: skip_newest={skip_newest + limit}")
        if next_hints:
            lines.extend(["", "Next: " + " | ".join(next_hints)])

        return {
            "operation": "pfc_check_task_status",
            "status": normalized_status,
            "task_id": task_id,
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "elapsed_time": data.get("elapsed_time"),
            "entry_script": data.get("entry_script") or data.get("script_path"),
            "description": data.get("description"),
            "checked": checked,
            "result": data.get("result"),
            "error": data.get("error"),
            "output": output_text,
            "output_mode": "windowed_snapshot",
            "pagination": pagination,
            "query": {
                "skip_newest": skip_newest,
                "limit": limit,
                "filter": filter,
                "wait_seconds": wait_seconds,
            },
            "display": "\n".join(lines),
        }
