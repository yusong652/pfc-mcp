# pfc-mcp

MCP server for [ITASCA PFC](https://www.itascacg.com/software/pfc) (Particle Flow Code) discrete element simulation control and documentation.

Provides 10 tools for browsing PFC documentation and controlling simulations through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## Quick Start

### Agentic Quick Start (Recommended)

Copy this instruction to your AI coding agent (Claude code / codex / gemini-cli / toyoura-nagisa):

```text
Fetch and follow this guide to initialize pfc-mcp end-to-end on this machine:
https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap.md
```

Detailed guide (human-readable):

- [docs/agentic/pfc-mcp-bootstrap.md](docs/agentic/pfc-mcp-bootstrap.md)

### Prerequisite

Install `uv` first (required for `uvx`):

- https://docs.astral.sh/uv/getting-started/installation/

### 1) Configure your MCP client

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["pfc-mcp"]
    }
  }
}
```

### 2) Start `pfc-mcp-bridge` in PFC GUI (execution tools only)

Execution tools require a running bridge in the PFC process.

Install/upgrade bridge package in PFC Python first (`>=0.1.2` recommended):

```bash
"{pfc_path}/exe64/python36/python.exe" -m pip install --user --upgrade pfc-mcp-bridge
```

Then start bridge in PFC GUI Python console:

```python
import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

Documentation tools work without the bridge.

### 3) Verify

Reconnect your MCP client and call a documentation tool such as `pfc_browse_commands`.

If `uvx` is not found, install `uv` or use fallback command `uv tool run pfc-mcp`.

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

## Runtime Model

- **pfc-mcp** (this package): MCP server with documentation tools and execution tool entrypoints.
- **[pfc-mcp-bridge](https://pypi.org/project/pfc-mcp-bridge/)**: bridge process that runs inside PFC GUI for simulation execution.
- Documentation tools work standalone; execution tools require a running bridge.

## Bridge in PFC GUI

Start `pfc-mcp-bridge` from the PFC GUI Python console when you need execution tools.

Expected startup output:

```
============================================================
PFC Bridge Server
============================================================
  URL:         ws://localhost:9001
  Log:         /your-working-dir/.pfc-bridge/bridge.log
  Callbacks:   Interrupt, Diagnostic (registered)
============================================================

Task loop running via Qt timer (interval=20ms, max_tasks_per_tick=1)
Bridge started in non-blocking mode (GUI remains responsive).
```

No Enter confirmation is required.

### Bridge Troubleshooting

- `Server won't start`: install bridge dependency in PFC Python:

```python
import pip
pip.main(['install', '--user', 'websockets==9.1'])
```

- `Tasks not processing`: ensure `pfc_mcp_bridge.start()` is running in the PFC process.
- `Connection failed`: verify bridge is running, port `9001` is free, and check `.pfc-bridge/bridge.log`.

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

- MCP server runtime: Python >= 3.10
- Bridge runtime (inside PFC): Python >= 3.6, ITASCA PFC 7.0+, `websockets==9.1`

## License

MIT - see [LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE).
