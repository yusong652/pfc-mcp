# pfc-mcp-bridge

`pfc-mcp-bridge` is the runtime bridge that runs inside a PFC process and enables execution tools used by `pfc-mcp`.

Use this package when you want MCP clients to run scripts and diagnostics in a live PFC session.

## Quick Start

Install and run in a PFC Python environment:

```python
import subprocess
subprocess.run(["pip", "install", "pfc-mcp-bridge"])

import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

Mode options:

- `mode="auto"` (default): try GUI/Qt first, fall back to blocking console pump
- `mode="gui"`: GUI/Qt only (non-blocking, required for plot capture)
- `mode="console"`: blocking console pump (task execution works; plot commands are unsupported)

Examples:

```python
# GUI mode (recommended when you need capture_plot)
pfc_mcp_bridge.start(mode="gui")

# Console mode
pfc_mcp_bridge.start(mode="console")
```

CLI:

```bash
pfc-mcp-bridge --mode auto --port 9001
```

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

## Requirements

- Python >= 3.6 (PFC embedded Python)
- ITASCA PFC 7.0+ with Python support
- `websockets==9.1`

## Troubleshooting

- `Server won't start`: in PFC Python, run `pip install websockets==9.1`
- `Connection failed`: check the bridge is running and port `9001` is available
- `No task execution`: keep `pfc_mcp_bridge.start()` running in the PFC process
- `pfc_capture_plot returns unsupported_in_console`: restart bridge in GUI mode (`pfc_mcp_bridge.start(mode="gui")`)

For full MCP client setup, see the main package page: [pfc-mcp](https://pypi.org/project/pfc-mcp/).

License: MIT ([LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)).
