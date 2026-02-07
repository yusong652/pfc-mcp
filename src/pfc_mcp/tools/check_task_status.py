"""Task status query tool backed by pfc-bridge."""

import asyncio

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client, get_task_manager
from pfc_mcp.tools.task_formatting import format_unix_timestamp, normalize_status, paginate_output
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
    ) -> str:
        """Check status and output for a submitted PFC task."""
        await asyncio.sleep(wait_seconds)

        client = await get_bridge_client()
        response = await client.check_task_status(task_id)

        status = response.get("status", "unknown")
        if status == "not_found":
            return (
                "Task not found\n"
                f"- task_id: {task_id}\n"
                "- status: not_found\n"
                "The task may have expired or the task ID is invalid."
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
            f"- git_commit: {(data.get('git_commit') or 'n/a')[:8] if data.get('git_commit') else 'n/a'}",
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

        return "\n".join(lines)
