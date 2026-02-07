"""
Utility message handlers.

Handles ping/pong heartbeat and task interruption.
"""

from datetime import datetime
from typing import Any, Dict

from .context import ServerContext
from .helpers import require_field


async def handle_ping(ctx, data):
    # type: (ServerContext, Dict[str, Any]) -> Dict[str, Any]
    """
    Handle ping heartbeat message.

    Args:
        ctx: Server context (unused, for interface consistency)
        data: Message data (unused, for interface consistency)

    Returns:
        Response dict with pong and timestamp
    """
    _ = ctx, data  # Unused, but required for consistent handler interface
    return {
        "type": "pong",
        "timestamp": datetime.now().isoformat()
    }


async def handle_interrupt_task(ctx, data):
    # type: (ServerContext, Dict[str, Any]) -> Dict[str, Any]
    """
    Handle interrupt_task message - request interrupt for a running task.

    Only sets interrupt flag for tasks that are actually running or pending.
    Returns error for completed/failed/interrupted tasks to prevent flag leaks.

    Args:
        ctx: Server context with dependencies
        data: Message data containing:
            - request_id: Request identifier
            - task_id: Task ID to interrupt

    Returns:
        Response dict with interrupt request result
    """
    from ..signals import request_interrupt

    request_id = data.get("request_id", "unknown")

    task_id, err = require_field(data, "task_id", request_id)
    if err:
        return err

    # Check if task exists and is interruptible
    task = ctx.task_manager.tasks.get(task_id)
    if not task:
        return {
            "type": "result",
            "request_id": request_id,
            "status": "error",
            "message": "Task not found: {}".format(task_id),
            "data": {"task_id": task_id, "interrupt_requested": False}
        }

    # Only allow interrupt for pending/running tasks
    task_status = task.status
    if task_status not in ("pending", "running"):
        return {
            "type": "result",
            "request_id": request_id,
            "status": "error",
            "message": "Task already in terminal state: {} (status: {})".format(task_id, task_status),
            "data": {"task_id": task_id, "status": task_status, "interrupt_requested": False}
        }

    # Request interrupt (will be checked by PFC callback)
    success = request_interrupt(task_id)
    if success:
        return {
            "type": "result",
            "request_id": request_id,
            "status": "success",
            "message": "Interrupt requested for task: {}".format(task_id),
            "data": {"task_id": task_id, "interrupt_requested": True}
        }
    else:
        return {
            "type": "result",
            "request_id": request_id,
            "status": "error",
            "message": "Failed to request interrupt",
            "data": None
        }
