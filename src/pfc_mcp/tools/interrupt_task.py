"""Task interruption tool backed by pfc-bridge."""

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.utils import TaskId


def register(mcp: FastMCP) -> None:
    """Register pfc_interrupt_task tool."""

    @mcp.tool()
    async def pfc_interrupt_task(task_id: TaskId) -> str:
        """Request graceful interruption of a running PFC task."""
        client = await get_bridge_client()
        response = await client.interrupt_task(task_id)

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

        return (
            "Interrupt request failed\n"
            f"- task_id: {task_id}\n"
            f"- status: {status}\n"
            f"- message: {message or 'unknown error'}"
        )
