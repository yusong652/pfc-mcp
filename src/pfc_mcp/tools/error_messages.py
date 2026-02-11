"""Backward-compatible error formatting exports for tools."""

from pfc_mcp.formatting import format_bridge_unavailable, format_operation_error, is_bridge_connectivity_error

__all__ = [
    "format_bridge_unavailable",
    "format_operation_error",
    "is_bridge_connectivity_error",
]
