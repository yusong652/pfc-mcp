"""
Workspace-related message handlers.

Handles workspace management operations like reset and directory queries.
"""

import logging
import os
from typing import Any, Dict

from .context import ServerContext

logger = logging.getLogger("PFC-Server")


async def handle_get_working_directory(ctx, data):
    # type: (ServerContext, Dict[str, Any]) -> Dict[str, Any]
    """
    Handle get_working_directory message.

    Args:
        ctx: Server context with dependencies
        data: Message data containing:
            - request_id: Request identifier

    Returns:
        Response dict with current working directory
    """
    request_id = data.get("request_id", "unknown")

    try:
        cwd = os.getcwd()

        return {
            "type": "result",
            "request_id": request_id,
            "status": "success",
            "message": f"PFC working directory: {cwd}",
            "data": {
                "working_directory": cwd
            }
        }
    except Exception as e:
        return {
            "type": "result",
            "request_id": request_id,
            "status": "error",
            "message": f"Failed to get working directory: {e}",
            "data": None
        }


async def handle_reset_workspace(ctx, data):
    # type: (ServerContext, Dict[str, Any]) -> Dict[str, Any]
    """
    Handle reset_workspace message - reset workspace state for testing.

    Resets:
    1. User console (deletes temporary scripts)
    2. Task history (clears all tasks)

    Args:
        ctx: Server context with dependencies
        data: Message data containing:
            - request_id: Request identifier
            - workspace_path: Path to workspace to reset

    Returns:
        Response dict with reset operation results
    """
    request_id = data.get("request_id", "unknown")
    workspace_path = data.get("workspace_path", "")

    try:
        results = []

        # 1. Reset user console (if manager exists for workspace)
        if workspace_path and workspace_path in ctx.user_console_managers:
            console_result = ctx.user_console_managers[workspace_path].reset()
            results.append(console_result)
            # Remove from cache after reset
            del ctx.user_console_managers[workspace_path]
        else:
            results.append({
                "success": True,
                "message": "No user console to reset",
                "deleted_scripts": 0
            })

        # 2. Clear all task history
        task_result = ctx.task_manager.clear_all_tasks()
        results.append(task_result)

        # Build summary
        all_success = all(r.get("success", False) for r in results)
        summary_parts = [r.get("message", "") for r in results]

        logger.info(
            "Workspace reset completed for: %s",
            workspace_path or "(no workspace)"
        )

        return {
            "type": "result",
            "request_id": request_id,
            "status": "success" if all_success else "partial",
            "message": "Workspace reset complete:\n- " + "\n- ".join(summary_parts),
            "data": {
                "user_console": results[0],
                "tasks": results[1],
            }
        }

    except Exception as e:
        logger.error(f"Workspace reset failed: {e}")
        return {
            "type": "result",
            "request_id": request_id,
            "status": "error",
            "message": f"Reset failed: {e}",
            "data": None
        }
