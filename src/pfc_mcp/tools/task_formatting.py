"""Formatting helpers for task-related PFC MCP tools."""

from datetime import datetime
from typing import Any, Optional


STATUS_MAP = {
    "pending": "pending",
    "running": "running",
    "success": "completed",
    "error": "failed",
    "interrupted": "interrupted",
    "not_found": "not_found",
}


def normalize_status(status: str) -> str:
    return STATUS_MAP.get(status, status)


def format_unix_timestamp(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        timestamp = float(value)
    except (TypeError, ValueError):
        return str(value)
    try:
        return datetime.fromtimestamp(timestamp).isoformat(sep=" ", timespec="seconds")
    except Exception:
        return str(value)


def paginate_output(
    output: str,
    skip_newest: int,
    limit: int,
    filter_text: Optional[str],
) -> tuple[str, dict[str, Any]]:
    lines = output.splitlines() if output else []
    if filter_text:
        lines = [line for line in lines if filter_text in line]

    total_lines = len(lines)
    start_idx = max(0, total_lines - limit - skip_newest)
    end_idx = max(0, total_lines - skip_newest)
    selected = lines[start_idx:end_idx]

    pagination = {
        "total_lines": total_lines,
        "line_range": f"{start_idx + 1}-{end_idx}" if selected else "0-0",
        "has_older": start_idx > 0,
        "has_newer": skip_newest > 0,
    }

    return "\n".join(selected) if selected else "(no output)", pagination
