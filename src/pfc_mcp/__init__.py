"""pfc-mcp - DEPRECATED. Superseded by the multi-engine ``itasca-mcp`` package.

This package no longer carries its own server. It depends on ``itasca-mcp`` and
runs it unchanged, after leading the MCP server ``instructions`` with a
migration notice so a connecting agent is told to switch. Frozen: no further
releases are planned.
"""

__version__ = "0.5.1"

import itasca_mcp.server as _itasca_server

_DEPRECATION = (
    "⚠️ DEPRECATED: the 'pfc-mcp' package is superseded by 'itasca-mcp', a "
    "single multi-engine server covering PFC, FLAC, 3DEC, MPoint, and MassFlow. "
    "This package now runs itasca-mcp unchanged and receives no further updates. "
    "Please update your MCP client config from `uvx pfc-mcp` to `uvx itasca-mcp`.\n\n"
)


def main() -> None:
    """Run the itasca-mcp server with a deprecation notice in its instructions."""
    _itasca_server.mcp.instructions = _DEPRECATION + (_itasca_server.mcp.instructions or "")
    _itasca_server.main()
