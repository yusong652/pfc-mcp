# Developer Guide: Install and Run from Source

This guide is for contributors who want to run `pfc-mcp` from a local checkout, test changes before publishing to PyPI, or install the bridge from local source into a PFC embedded Python environment.

## Runtime Split

This repository contains two separate runtimes:

- `pfc-mcp`
  The MCP server package under [`src/pfc_mcp`](../../src/pfc_mcp), running on standard Python `>=3.10`
- `pfc-mcp-bridge`
  The bridge package under [`pfc-mcp-bridge`](../../pfc-mcp-bridge), running inside PFC embedded Python

Treat them as separate installation targets even though they live in the same repository.

## 1. Clone and Install Dev Dependencies

From the repository root:

```bash
uv sync --group dev
```

Useful local commands:

```bash
uv run pytest tests
uv run pfc-mcp
```

## 2. Point Your MCP Client at the Local Checkout

If you want your MCP client to use local source instead of the published PyPI package, point it at the repository with `uv run --directory`:

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/pfc-mcp", "pfc-mcp"]
    }
  }
}
```

This is the simplest way to test MCP-side changes without building or publishing packages.

## 3. Run the Bridge Directly from Source

If you only need bridge-side changes to take effect in PFC, you do not need to install the bridge package at all. In the PFC IPython console:

```python
%run C:/path/to/pfc-mcp/pfc-mcp-bridge/start_bridge.py
```

Notes:

- Use forward slashes in the path.
- Do not wrap the `%run` path in quotes.
- Restart the bridge after source changes.

This is the fastest workflow for bridge development.

## 4. Install the Bridge from Local Source into Embedded Python

If you want to test the package installation path itself, install `pfc-mcp-bridge` from local source using the embedded Python interpreter from a terminal.

Pick the correct interpreter for your PFC version:

- PFC `6.0` / `7.0`: `C:/Program Files/Itasca/.../exe64/python36/python.exe`
- PFC `9.0`: `C:/Program Files/Itasca/.../exe64/python310/python.exe`

Example commands:

```powershell
& "C:\Program Files\Itasca\PFC700\exe64\python36\python.exe" -m pip install --user -e C:\path\to\pfc-mcp\pfc-mcp-bridge
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -m pip install --user -e C:\path\to\pfc-mcp\pfc-mcp-bridge
```

Why use the embedded interpreter from a terminal:

- It installs into the exact Python environment used by PFC.
- It avoids relying on `subprocess` calls from inside the PFC console.
- It is the most reliable workflow for editable installs.

The bridge package will pull a matching `websockets` version automatically:

- Python `3.6` -> `websockets==9.1`
- Python `3.10` -> `websockets==16.0`

## 5. Install from Inside PFC IPython

For PyPI-based installation inside the PFC console, use the version-aware snippet from the main README:

- PFC `6.0` / `7.0`: `pip.main(...)`
- PFC `9.0`: `pip._internal.cli.main.main(...)`

For source installs, prefer the terminal-based embedded-interpreter workflow from Step 4 instead of trying to drive an editable install from inside the PFC GUI console.

## 6. Verify the Environment

Verify the bridge package inside embedded Python:

```powershell
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -c "import pfc_mcp_bridge, websockets; print(pfc_mcp_bridge.__version__); print(websockets.__version__)"
```

Then start the bridge in PFC and verify from your MCP client:

1. Start the bridge in PFC with `pfc_mcp_bridge.start()` or `%run .../start_bridge.py`
2. Restart the MCP client session
3. Call `pfc_list_tasks`

## 7. Recommended Dev Loop

For most day-to-day work:

1. Run `uv sync --group dev`
2. Point your MCP client at the local checkout with `uv run --directory`
3. Use `%run .../pfc-mcp-bridge/start_bridge.py` inside PFC
4. Run `uv run pytest tests`
5. Restart the MCP client and bridge after changes when needed
