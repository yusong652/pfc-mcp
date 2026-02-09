"""PFC MCP Server - ITASCA PFC tools exposed over MCP."""

from fastmcp import FastMCP

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
        "PFC (Particle Flow Code) documentation server. "
        "Provides tools for browsing/searching documentation and for executing tasks "
        "through a pfc-bridge WebSocket service running inside PFC GUI."
    ),
)

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
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
