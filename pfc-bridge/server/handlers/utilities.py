"""
Utility message handlers.

Handles ping/pong heartbeat.
"""

from datetime import datetime
from typing import Any, Dict

from .context import ServerContext


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
