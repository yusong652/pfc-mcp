<p align="center">
  <img src="https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/header.gif" alt="pfc-mcp" width="70%">
</p>

# pfc-mcp

[English](https://github.com/yusong652/pfc-mcp/blob/main/README.md) | [简体中文](https://github.com/yusong652/pfc-mcp/blob/main/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp)](https://pypi.org/project/pfc-mcp/)
[![Downloads](https://static.pepy.tech/badge/pfc-mcp)](https://pepy.tech/project/pfc-mcp)
[![GitHub stars](https://img.shields.io/github/stars/yusong652/pfc-mcp)](https://github.com/yusong652/pfc-mcp/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

`pfc3d>model new ;now, with LLM.`

**pfc-mcp** connects AI agents to [ITASCA PFC](https://www.itascacg.com/software/pfc) — Itasca's discrete element method (DEM) code — through the [Model Context Protocol](https://modelcontextprotocol.io/). Browse documentation, run simulations, and execute code, all through natural conversation.

`pfc3d>model solve ;LLM solves.`

![pfc-mcp demo](https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/pfc-mcp.gif)

## Tools (10)

**5 documentation tools** — browse and search PFC commands, Python API, and reference docs. No bridge required.

**5 execution tools** — interactive REPL, task submission, progress monitoring, interruption, and history. Requires bridge.

## First-time Setup

### Prerequisites

- **ITASCA PFC 6.0, 7.0, or 9.0** installed
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

**2. Start the bridge from inside PFC:**

Download [`addon.py`](addon.py), then use either of these two flows inside PFC:

- Copy the file contents into the PFC IPython console and run them
- Or download the file and execute it in PFC GUI

<img src="https://raw.githubusercontent.com/yusong652/pfc-mcp/assets/addon.gif" alt="addon.py demo" width="60%">

### Verify

Restart your AI agent (Claude Code, Codex CLI, Gemini CLI, etc.) and ask it to call `pfc_execute_code` to verify the connection.

## Daily Startup

Once first-time setup is done, each new PFC session only needs the bridge re-started — run this in PFC's IPython console and you're back online:

```python
import itasca_mcp_bridge
itasca_mcp_bridge.start()
```

`start()` checks PyPI for a newer bridge release and self-upgrades before starting (best-effort: offline machines just start the installed version; pass `auto_upgrade=False` to pin). The MCP client config persists.

## Features

- **Multi-version PFC support** - command docs for PFC 6.0, 7.0, and 9.0 via the `version` parameter
- **Hierarchical documentation browsing** - agents navigate the PFC command tree to discover capabilities and boundaries, reducing hallucinated commands
- **Enhanced plot documentation** - plot items reference docs supplementing the official documentation
- **Interactive REPL** - rapid iteration before committing to full scripts; agents can quickly test and refine code
- **Task lifecycle management** - submit long-running simulations, monitor progress, interrupt running tasks, and browse task history
- **Multi-client compatible** - works with Claude Code, Codex CLI, Gemini CLI, GitHub Copilot CLI, OpenCode, toyoura-nagisa, and other MCP clients

## Troubleshooting

See [Troubleshooting](docs/agentic/pfc-mcp-bootstrap.md#troubleshooting) in the bootstrap guide.

## Development

See [Developer Guide: Install and Run from Source](docs/development/source-install.md).

<a href="https://glama.ai/mcp/servers/yusong652/pfc-mcp">
  <img width="200" height="105" src="https://glama.ai/mcp/servers/yusong652/pfc-mcp/badge" alt="pfc-mcp MCP server" />
</a>

## Contributing

PRs and issues are welcome! See the [Developer Guide](docs/development/source-install.md) to get started.

## License

MIT - see [LICENSE](LICENSE).

<!-- mcp-name: io.github.yusong652/pfc -->
