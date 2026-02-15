"""Task interruption tool backed by pfc-bridge."""

from typing import Any

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.contracts import build_error_from_legacy, build_ok
from pfc_mcp.formatting import format_bridge_unavailable, format_operation_error
from pfc_mcp.utils import TaskId


def register(mcp: FastMCP) -> None:
    """Register pfc_interrupt_task tool."""

    @mcp.tool()
    async def pfc_interrupt_task(task_id: TaskId) -> dict[str, Any]:
        """Request graceful interruption of a running PFC task."""
        try:
            client = await get_bridge_client()
            response = await client.interrupt_task(task_id)
        except Exception as exc:
            return build_error_from_legacy(
                format_bridge_unavailable("pfc_interrupt_task", exc, task_id=task_id)
            )

        status = response.get("status", "unknown")
        message = response.get("message", "")

        if status == "success":
            return build_ok(
                {
                    "task_id": task_id,
                    "interrupt_requested": True,
                    "message": message or "signal sent",
                    "next_action": f'call pfc_check_task_status(task_id="{task_id}")',
                }
            )

        return build_error_from_legacy(
            format_operation_error(
                "pfc_interrupt_task",
                status=status or "interrupt_failed",
                message=message or "Interrupt request failed",
                task_id=task_id,
                action="Check task status and bridge logs",
            )
        )
