# pfc-mcp Agent Bootstrap Guide

Use this guide when an agent needs to set up `pfc-mcp` execution end-to-end on a Windows machine.

## Target Outcome

1. MCP client is configured to run `pfc-mcp`.
2. `pfc-mcp-bridge` is installed in PFC embedded Python (`>=0.1.2`).
3. Bridge is started in PFC GUI (`pfc_mcp_bridge.start()`).
4. MCP execution tools are verified with `pfc_list_tasks`.

## Agent Execution Rules

- Use bounded, fast path detection for `pfc_path`; avoid full-drive recursive scans by default.
- Prefer PFC embedded interpreter for package install:
  - `"{pfc_path}/exe64/python36/python.exe" -m pip ...`
- If a step fails, report the exact command and output, then apply the next fallback.

## Step 1 - Configure MCP Client

Ensure MCP client config includes:

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

If `uvx` is unavailable, install `uv` first.

## Step 2 - Resolve `pfc_path`

`pfc_path` should be the PFC install directory containing `exe64/pfc3d700_gui.exe`.

### 2.1 Fast registry lookup

```powershell
$keys=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*');
$hits=@();
foreach($k in $keys){
  Get-ItemProperty $k -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -match 'PFC|Itasca' } |
    ForEach-Object {
      if($_.InstallLocation){
        $exe=Join-Path $_.InstallLocation 'exe64\pfc3d700_gui.exe';
        if(Test-Path $exe){ $hits+=$exe }
      }
    }
}
$hits | Select-Object -Unique | Select-Object -First 3
```

### 2.2 Bounded common-path lookup

```powershell
$roots=@('C:\Program Files\Itasca','D:\Program Files\Itasca','C:\Itasca','D:\Itasca');
$hits=@();
foreach($r in $roots){
  if(Test-Path $r){
    Get-ChildItem $r -Directory -ErrorAction SilentlyContinue | ForEach-Object {
      $exe=Join-Path $_.FullName 'exe64\pfc3d700_gui.exe';
      if(Test-Path $exe){ $hits+=$exe }
    }
  }
}
$hits | Select-Object -Unique | Select-Object -First 3
```

If still unresolved, ask user to provide exact `pfc_path`.

## Step 3 - Install/Upgrade Bridge in PFC Python

Check current package:

```bash
"{pfc_path}/exe64/python36/python.exe" -m pip show pfc-mcp-bridge
```

Install/upgrade to required version:

```bash
"{pfc_path}/exe64/python36/python.exe" -m pip install --user --upgrade pfc-mcp-bridge
```

Verify import and version:

```bash
"{pfc_path}/exe64/python36/python.exe" -c "import pfc_mcp_bridge; print(pfc_mcp_bridge.__version__)"
```

If websocket dependency errors appear, install:

```bash
"{pfc_path}/exe64/python36/python.exe" -m pip install --user websockets==9.1
```

## Step 4 - Start Bridge in PFC GUI

In PFC GUI Python console:

```python
import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

Expected output includes:

- `PFC Bridge Server`
- `ws://localhost:9001`
- `Bridge started in non-blocking mode`

## Step 5 - Verify from MCP Client

Reconnect MCP client and call:

- `pfc_list_tasks`

If it succeeds, setup is complete.

## Troubleshooting

- `Connection refused`:
  - Bridge not running in PFC GUI, or port `9001` not available.
- `No module named pfc_mcp_bridge`:
  - Bridge package not installed in PFC embedded Python.
- `No module named websockets`:
  - Install `websockets==9.1` in PFC embedded Python.
- `status remains pending / plot diagnostic timeout during solve`:
  - Upgrade to `pfc-mcp-bridge >= 0.1.2`.
