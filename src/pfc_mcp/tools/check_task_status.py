"""Task status query tool backed by pfc-bridge."""

import asyncio
from typing import Any

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client, get_task_manager
from pfc_mcp.contracts import build_ok
from pfc_mcp.formatting import (
    build_bridge_error,
    build_operation_error,
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
            return build_bridge_error(exc, task_id=task_id)

        status = response.get("status", "unknown")
        if status == "not_found":
            return build_operation_error(
                "not_found",
                "Task not found",
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

        get_task_manager().update_status(task_id, normalized_status)

        result: dict[str, Any] = {
            "task_id": task_id,
            "task_status": normalized_status,
            "start_time": format_unix_timestamp(data.get("start_time")),
            "end_time": format_unix_timestamp(data.get("end_time")),
            "elapsed_time": data.get("elapsed_time"),
            "entry_script": data.get("entry_script") or data.get("script_path"),
            "description": data.get("description"),
            "output": output_text,
            "pagination": pagination,
        }

        if data.get("result") is not None:
            result["result"] = data["result"]
        if data.get("error"):
            result["error"] = data["error"]

        return build_ok(result)
