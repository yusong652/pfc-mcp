# pfc-mcp

MCP server for [ITASCA PFC](https://www.itascacg.com/software/pfc) (Particle Flow Code) discrete element simulation control and documentation.

Provides 10 tools for browsing PFC documentation and controlling simulations through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## Quick Start

### Run with uvx (no install)

```bash
uvx pfc-mcp
```

### Or install and run

```bash
pip install pfc-mcp
pfc-mcp
```

### MCP Client Configuration

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "command": "uvx",
      "args": ["pfc-mcp"]
    }
  }
}
```

## Tools

### Documentation (5 tools)

| Tool | Description |
|------|-------------|
| `pfc_browse_commands` | Browse PFC command documentation by path |
| `pfc_browse_python_api` | Browse PFC Python SDK documentation by path |
| `pfc_browse_reference` | Browse reference docs (contact models, range elements) |
| `pfc_query_command` | Search PFC commands by keywords |
| `pfc_query_python_api` | Search PFC Python SDK by keywords |

### Execution (5 tools)

| Tool | Description |
|------|-------------|
| `pfc_execute_task` | Submit a Python script for execution in PFC |
| `pfc_check_task_status` | Check status and output of a running/completed task |
| `pfc_list_tasks` | List tracked tasks with pagination |
| `pfc_interrupt_task` | Request graceful interruption of a running task |
| `pfc_capture_plot` | Capture a PFC plot image with configurable camera and coloring |

## Architecture

```
+-------------------+       stdio        +-------------------+    WebSocket    +------------------+
|  MCP Client       | <----------------> |  pfc-mcp          | <------------> |  pfc-mcp-bridge  |
|  (Claude, etc.)   |       MCP          |  (this package)   |   ws://9001    |  (in PFC GUI)    |
+-------------------+                    +-------------------+                +------------------+
                                          Python 3.10+                         Python 3.6+
                                          Any machine                          PFC GUI process
```

- **pfc-mcp** (this package): MCP server with documentation tools and WebSocket client for execution
- **[pfc-mcp-bridge](pfc-bridge/)**: WebSocket server that runs inside PFC GUI for thread-safe simulation control

Documentation tools work standalone. Execution tools require a running pfc-mcp-bridge instance.

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PFC_MCP_BRIDGE_URL` | `ws://localhost:9001` | WebSocket URL of pfc-mcp-bridge |
| `PFC_MCP_WORKSPACE_PATH` | _(none)_ | Working directory for script execution |
| `PFC_MCP_REQUEST_TIMEOUT_S` | `10.0` | WebSocket request timeout (seconds) |
| `PFC_MCP_MAX_RETRIES` | `2` | Connection retry attempts |
| `PFC_MCP_AUTO_RECONNECT` | `true` | Auto-reconnect on connection loss |
| `PFC_MCP_DIAGNOSTIC_TIMEOUT_MS` | `30000` | Timeout for diagnostic operations (ms) |

## Development

```bash
# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run server locally
uv run pfc-mcp
```

## Requirements

- Python >= 3.10
- For execution tools: a running [pfc-mcp-bridge](pfc-bridge/) instance in PFC GUI

## License

MIT - see [LICENSE](LICENSE).
