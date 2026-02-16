# pfc-mcp

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp)](https://pypi.org/project/pfc-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

**MCP server that gives AI agents full access to [ITASCA PFC](https://www.itascacg.com/software/pfc) - browse documentation, run simulations, capture plots, all through natural conversation.**

Built on the [Model Context Protocol](https://modelcontextprotocol.io/), pfc-mcp turns any MCP-compatible AI client (Claude Code, Codex CLI, Gemini CLI, OpenCode, toyoura-nagisa, etc.) into a PFC co-pilot that can look up commands, execute scripts, monitor long-running simulations, and capture visualizations.

![pfc-mcp demo](https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/pfc-mcp.gif)

## Tools (10)

### Documentation (5) - no bridge required

- Browse PFC command tree, Python SDK reference, and reference docs (contact models, range elements)
- Search commands and Python APIs by keyword (BM25 ranked)

### Execution (5) - requires bridge in a running PFC process

- Submit Python scripts and poll status/output in real time
- List and manage tasks across sessions
- Interrupt running simulations
- Capture PFC plot images with configurable camera, coloring, and cut planes

## Quick Start

### Prerequisites

- **ITASCA PFC 7.0** installed (`pfc2d700_gui.exe` or `pfc3d700_gui.exe`)
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** installed (for `uvx`)

### Agentic Setup (Recommended)

Copy this to your AI agent and let it self-configure:

```text
Fetch and follow this bootstrap guide end-to-end:
https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap.md
```

### Manual Setup

**1. Register the MCP server** in your client config:

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

**2. Install dependency:**

```python
import subprocess
subprocess.run(["pip", "install", "pfc-mcp-bridge"])
```

### Start Bridge & Verify

```python
import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

![PFC GUI Python console](https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/init.png)

**Verify** - reconnect your MCP client and ask the agent to call `pfc_list_tasks` to verify the full MCP + bridge connection.

## Design Highlights

- **Documentation as a boundary map** - browse and search tools let agents discover what PFC can do, reducing hallucinated commands
- **Task queue with live status** - scripts are queued and executed sequentially; agents can poll output and status in real time
- **Callback-based control** - gracefully interrupt long-running `cycle()` calls, and capture plots mid-simulation without pausing it

## Runtime Model

| Component | PyPI | Python | Role |
|-----------|------|--------|------|
| **pfc-mcp** | [![PyPI](https://img.shields.io/pypi/v/pfc-mcp)](https://pypi.org/project/pfc-mcp/) | >= 3.10 | MCP server (documentation + execution client) |
| **pfc-mcp-bridge** | [![PyPI](https://img.shields.io/pypi/v/pfc-mcp-bridge)](https://pypi.org/project/pfc-mcp-bridge/) | >= 3.6 | WebSocket bridge inside PFC process (GUI or console) |

Documentation tools work standalone. Execution tools require a running bridge.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uvx` not found | [Install uv](https://docs.astral.sh/uv/getting-started/installation/) or use `uv tool run pfc-mcp` |
| Bridge won't start | Install dependency in PFC Python: `pip install websockets==9.1` |
| Tasks not processing | Ensure `pfc_mcp_bridge.start()` is running in PFC |
| `pfc_capture_plot` unsupported | Plot capture requires PFC GUI; console mode does not support it |
| Connection failed | Check bridge is running, port 9001 is free, see `.pfc-bridge/bridge.log` |

## Development

```bash
uv sync --group dev    # Install with dev dependencies
uv run pytest          # Run tests
uv run pfc-mcp         # Run server locally
```

## License

MIT - see [LICENSE](LICENSE).
