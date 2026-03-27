# pfc-mcp-bridge

[English](https://github.com/yusong652/pfc-mcp/blob/main/pfc-mcp-bridge/README.md) | [简体中文](https://github.com/yusong652/pfc-mcp/blob/main/pfc-mcp-bridge/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/pfc-mcp-bridge)](https://pypi.org/project/pfc-mcp-bridge/)

Runtime bridge that runs inside a PFC process and enables execution tools for [pfc-mcp](https://pypi.org/project/pfc-mcp/).

## Quick Start

Install and run in PFC Python console:

```python
import sys

if sys.version_info < (3, 10):
    import pip

    pip.main(["install", "--user", "-U", "pfc-mcp-bridge"])
else:
    from pip._internal.cli.main import main as pip_main

    pip_main(["install", "--user", "-U", "pfc-mcp-bridge"])

import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

The bridge auto-detects the runtime: Qt timer in GUI, blocking loop in console.
Installing `pfc-mcp-bridge` from the PFC IPython console also installs a matching `websockets` version automatically: `9.1` for PFC 6/7 and `16.0` for PFC 9. The snippet uses `pip.main(...)` on PFC 6/7 and `pip._internal.cli.main.main(...)` on PFC 9.

Expected output:

```text
============================================================
PFC Bridge Server
============================================================
  URL:         ws://localhost:9001
  Log:         /your-working-dir/.pfc-mcp-bridge/bridge.log
  Callbacks:   Interrupt, Diagnostic (registered)
============================================================
```

## Requirements

- Python >= 3.6 (PFC 6/7 use Python 3.6; PFC 9 uses Python 3.10)
- ITASCA PFC 6.0, 7.0, or 9.0
- `pfc-mcp-bridge` installs a matching `websockets` dependency automatically: `websockets==9.1` on Python 3.6, `websockets==16.0` on Python 3.10

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Server won't start | In the PFC Python/IPython console, rerun the version-aware install snippet above (`pip.main(...)` on PFC 6/7, `pip._internal.cli.main.main(...)` on PFC 9) |
| `websockets` version mismatch in PFC 9 | In the PFC 9 IPython console, run `from pip._internal.cli.main import main as pip_main; pip_main(["install", "--user", "websockets==16.0"])` |
| Port in use | Use `pfc_mcp_bridge.start(port=9002)` in PFC Python, then set MCP server env `PFC_MCP_BRIDGE_URL=ws://localhost:9002` |
| Connection failed | Check bridge is running, port is available, see `.pfc-mcp-bridge/bridge.log` |
| No task execution / cannot connect from MCP | If execution tools return `ok=false`, `error.code=bridge_unavailable`, and `error.details.reason=cannot connect to bridge service`, ensure bridge is running in PFC (`pfc_mcp_bridge.start()`) and `PFC_MCP_BRIDGE_URL` matches bridge URL |

## Development

For the full local-source workflow, see [Developer Guide: Install and Run from Source](../docs/development/source-install.md).

To run the bridge from a local source checkout (without installing from PyPI), use `%run` in the PFC IPython console:

```python
%run C:/path/to/pfc-mcp/pfc-mcp-bridge/start_bridge.py
```

> **Note:** Use forward slashes in the path. Do not wrap it in quotes.

This is equivalent to the PyPI workflow but loads the source directly, so code changes take effect immediately on restart.

For full MCP client setup, see [pfc-mcp](https://pypi.org/project/pfc-mcp/).

License: MIT ([LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)).
