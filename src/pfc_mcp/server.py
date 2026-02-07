"""PFC MCP Server - ITASCA PFC discrete element simulation tools via MCP.

Provides documentation browsing and search tools for PFC commands,
Python SDK API, and reference documentation.
"""

from fastmcp import FastMCP

from pfc_mcp.tools import (
    browse_commands,
    browse_python_api,
    browse_reference,
    query_command,
    query_python_api,
)

mcp = FastMCP(
    "PFC MCP Server",
    instructions=(
        "PFC (Particle Flow Code) documentation server. "
        "Provides tools for browsing and searching ITASCA PFC command documentation, "
        "Python SDK API documentation, and reference documentation (contact models, range elements). "
        "Use browse tools for hierarchical navigation, query tools for keyword search."
    ),
)

# Register all doc tools
browse_commands.register(mcp)
browse_python_api.register(mcp)
browse_reference.register(mcp)
query_command.register(mcp)
query_python_api.register(mcp)


def main():
    """Entry point for the PFC MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
