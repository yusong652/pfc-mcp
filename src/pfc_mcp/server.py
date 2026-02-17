"""PFC MCP Server - ITASCA PFC tools exposed over MCP."""

import argparse
import asyncio
import logging

from fastmcp import FastMCP

from pfc_mcp import __version__
from pfc_mcp.bridge import close_bridge_client
from pfc_mcp.tools import (
    browse_commands,
    browse_python_api,
    browse_reference,
    capture_plot,
    check_task_status,
    execute_task,
    interrupt_task,
    list_tasks,
    query_command,
    query_python_api,
)

mcp = FastMCP(
    "PFC MCP Server",
    instructions=(
        "PFC (Particle Flow Code) MCP server. "
        "Provides tools for browsing/searching PFC documentation "
        "and for executing simulation tasks, capturing plots, and managing runs "
        "through a pfc-bridge WebSocket service running inside PFC GUI."
    ),
)

logger = logging.getLogger("pfc-mcp.server")

# Register documentation tools
browse_commands.register(mcp)
browse_python_api.register(mcp)
browse_reference.register(mcp)
query_command.register(mcp)
query_python_api.register(mcp)

# Register execution tools
execute_task.register(mcp)
check_task_status.register(mcp)
list_tasks.register(mcp)
interrupt_task.register(mcp)
capture_plot.register(mcp)


def main():
    """Entry point for the PFC MCP server."""
    parser = argparse.ArgumentParser(
        prog="pfc-mcp",
        description="PFC MCP Server - ITASCA PFC tools exposed over MCP",
    )
    parser.add_argument("--version", "-v", action="version", version=f"pfc-mcp {__version__}")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind when using http/sse transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind when using http/sse transport (default: 8000)",
    )
    args = parser.parse_args()

    run_kwargs: dict = {"transport": args.transport, "show_banner": False}
    if args.transport in ("http", "sse"):
        run_kwargs["host"] = args.host
        run_kwargs["port"] = args.port

    # Suppress noisy uvicorn shutdown messages (e.g. "Cancel N running task(s)")
    logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)

    try:
        mcp.run(**run_kwargs)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            asyncio.run(close_bridge_client())
        except Exception as exc:
            logger.debug("Bridge client cleanup skipped: %s", exc)


if __name__ == "__main__":
    main()
