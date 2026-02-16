"""
Workspace-related message handlers.
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger("PFC-Server")


async def handle_get_working_directory(ctx, data):
    # type: (Any, Dict[str, Any]) -> Dict[str, Any]
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
                "working_directory": cwd,
                "runtime_mode": getattr(ctx, "runtime_mode", "unknown"),
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
