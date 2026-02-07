"""Friendly error rendering helpers for MCP tool outputs."""

from __future__ import annotations

from pfc_mcp.config import get_bridge_config


def is_bridge_connectivity_error(exc: Exception) -> bool:
    """Best-effort detection for bridge connectivity failures."""
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True

    lowered = str(exc).strip().lower()
    return (
        "connect call failed" in lowered
        or "connection refused" in lowered
        or "connection lost" in lowered
        or "connection closed" in lowered
        or "bridge" in lowered and "unavailable" in lowered
        or "[errno 61]" in lowered
    )


def _summarize_bridge_error(exc: Exception) -> str:
    text = str(exc).strip()
    lowered = text.lower()

    if "connect call failed" in lowered or "connection refused" in lowered or "[errno 61]" in lowered:
        return "cannot connect to bridge service"
    if "timed out" in lowered:
        return "bridge request timed out"
    if "connection closed" in lowered or "connection lost" in lowered:
        return "bridge connection closed"
    if not text:
        return "unknown bridge error"
    return text.splitlines()[0]


def format_bridge_unavailable(operation: str, exc: Exception, task_id: str | None = None) -> dict[str, str]:
    """Return structured bridge connectivity error payload.

    The dict is returned directly from MCP tools so FastMCP can expose
    `structuredContent.status`, allowing backend to parse errors by status
    instead of brittle text matching.
    """
    cfg = get_bridge_config()
    reason = _summarize_bridge_error(exc)

    display_lines = [
        f"PFC bridge unavailable ({operation})",
        "- status: bridge_unavailable",
        f"- bridge_url: {cfg.url}",
        f"- reason: {reason}",
        "- action: start pfc-bridge in PFC GUI, then retry",
    ]
    if task_id:
        display_lines.append(f"- task_id: {task_id}")

    return {
        "status": "bridge_unavailable",
        "operation": operation,
        "message": "PFC bridge unavailable",
        "bridge_url": cfg.url,
        "reason": reason,
        "action": "start pfc-bridge in PFC GUI, then retry",
        "task_id": task_id or "",
        "display": "\n".join(display_lines),
    }


def format_operation_error(
    operation: str,
    status: str,
    message: str,
    reason: str | None = None,
    task_id: str | None = None,
    action: str | None = None,
) -> dict[str, str]:
    """Return structured operation error payload with human-readable display."""
    display_lines = [
        f"{operation} failed",
        f"- status: {status}",
        f"- message: {message}",
    ]
    if reason:
        display_lines.append(f"- reason: {reason}")
    if task_id:
        display_lines.append(f"- task_id: {task_id}")
    if action:
        display_lines.append(f"- action: {action}")

    return {
        "status": status,
        "operation": operation,
        "message": message,
        "reason": reason or "",
        "task_id": task_id or "",
        "action": action or "",
        "display": "\n".join(display_lines),
    }
