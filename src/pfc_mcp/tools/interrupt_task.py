"""Task interruption tool backed by pfc-bridge."""

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.tools.error_messages import format_bridge_unavailable, format_operation_error
from pfc_mcp.utils import TaskId


def register(mcp: FastMCP) -> None:
    """Register pfc_interrupt_task tool."""

    @mcp.tool()
    async def pfc_interrupt_task(task_id: TaskId) -> str | dict[str, str]:
        """Request graceful interruption of a running PFC task."""
        try:
            client = await get_bridge_client()
            response = await client.interrupt_task(task_id)
        except Exception as exc:
            return format_bridge_unavailable("pfc_interrupt_task", exc, task_id=task_id)

        status = response.get("status", "unknown")
        message = response.get("message", "")

        if status == "success":
            return (
                "Interrupt requested\n"
                f"- task_id: {task_id}\n"
                "- interrupt_requested: true\n"
                f"- message: {message or 'signal sent'}\n\n"
                f'Next: call pfc_check_task_status(task_id="{task_id}") to confirm final state.'
            )

        return format_operation_error(
            "pfc_interrupt_task",
            status=status or "interrupt_failed",
            message=message or "Interrupt request failed",
            task_id=task_id,
            action="Check task status and bridge logs",
        )
