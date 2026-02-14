# pfc-mcp-bridge

`pfc-mcp-bridge` is the runtime bridge that runs inside PFC GUI and enables execution tools used by `pfc-mcp`.

Use this package when you want MCP clients to run scripts and diagnostics in a live PFC session.

## Quick Start

Run in the PFC GUI Python console:

```python
import subprocess
subprocess.run(["pip", "install", "pfc-mcp-bridge"])

import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

Expected startup output:

```
============================================================
PFC Bridge Server
============================================================
  URL:         ws://localhost:9001
  Log:         /your-working-dir/.pfc-bridge/bridge.log
  Running:     True
  Features:    PFC, Interrupt, Diagnostic
============================================================

Task loop running (Ctrl+C to stop)...
```

After startup banner, press Enter in the PFC Python console to start the task loop.

## Requirements

- Python >= 3.6 (PFC embedded Python)
- ITASCA PFC 7.0+ with Python support
- `websockets==9.1`

## Troubleshooting

- `Server won't start`: in PFC Python, run `pip install websockets==9.1`
- `Connection failed`: check the bridge is running and port `9001` is available
- `No task execution`: keep `pfc_mcp_bridge.start()` running in the PFC process

For full MCP client setup, see the main package page: [pfc-mcp](https://pypi.org/project/pfc-mcp/).

License: MIT ([LICENSE](https://github.com/yusong652/pfc-mcp/blob/main/LICENSE)).
