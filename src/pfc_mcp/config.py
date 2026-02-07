"""Runtime configuration for PFC MCP server."""

from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class BridgeConfig:
    url: str
    default_session_id: str
    reconnect_interval_s: float
    max_retries: int
    request_timeout_s: float
    workspace_path: str | None
    auto_reconnect: bool


def get_bridge_config() -> BridgeConfig:
    """Load bridge config from environment variables."""
    workspace = os.getenv("PFC_MCP_WORKSPACE_PATH")
    return BridgeConfig(
        url=os.getenv("PFC_MCP_BRIDGE_URL", "ws://localhost:9001"),
        default_session_id=os.getenv("PFC_MCP_SESSION_ID", "mcp"),
        reconnect_interval_s=_env_float("PFC_MCP_RECONNECT_INTERVAL_S", 0.5),
        max_retries=max(0, _env_int("PFC_MCP_MAX_RETRIES", 2)),
        request_timeout_s=max(1.0, _env_float("PFC_MCP_REQUEST_TIMEOUT_S", 10.0)),
        workspace_path=workspace if workspace else None,
        auto_reconnect=_env_bool("PFC_MCP_AUTO_RECONNECT", True),
    )
