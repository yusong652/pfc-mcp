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
- Respect step ownership labels:
  - `[AGENT]` means the agent should execute the action.
  - `[USER ACTION REQUIRED]` means the user must execute it manually.

## Step 1 - Configure MCP Client

[AGENT]

Ensure MCP client config includes:

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

Client config path notes:

- Claude Code: workspace `.mcp.json` (or user-level MCP config if configured that way)
- Other clients (codex / opencode / gemini-cli / toyoura-nagisa): use each client's MCP config file format/path

When editing MCP config, use this order:

1. If config file does not exist, create it.
2. If config exists but has no `pfc-mcp` entry, merge/add only that entry.
3. If `pfc-mcp` already exists, validate/update only `type`, `command`, and `args`.
4. Do not overwrite unrelated MCP servers.

If `uvx` is unavailable, install `uv` first, then use fallback command:

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["tool", "run", "pfc-mcp"]
    }
  }
}
```

## Step 2 - Resolve `pfc_path`

[AGENT]

`pfc_path` should be the PFC install directory containing `exe64/pfc*_gui.exe`.

### 2.0 Quick probe (fast path)

Try lightweight checks first:

```bash
ls "C:/Program Files/Itasca"
ls "D:/Program Files/Itasca"
```

If obvious install folders are found, check `exe64` inside those folders before running the full PowerShell lookup.

### 2.1 Bounded common-path lookup (recommended)

Run in PowerShell (not bash) to avoid `$` variable expansion issues:

```powershell
$roots=@('C:\Program Files\Itasca','D:\Program Files\Itasca','C:\Itasca','D:\Itasca');
$hits=@();
foreach($r in $roots){
  if(Test-Path $r){
    Get-ChildItem -Path $r -Directory -ErrorAction SilentlyContinue | ForEach-Object {
      $exeDir=Join-Path $_.FullName 'exe64';
      if(Test-Path $exeDir){
        Get-ChildItem -Path $exeDir -Filter 'pfc*_gui.exe' -File -ErrorAction SilentlyContinue | ForEach-Object {
          $hits += [PSCustomObject]@{ pfc_path=$_.Directory.Parent.FullName; gui_exe=$_.FullName }
        }
      }
    }
  }
}
$hits | Sort-Object gui_exe -Unique | Select-Object -First 5
```

If the agent shell is bash on Windows, wrap the PowerShell script in single quotes:

```bash
powershell -NoProfile -Command '& {$roots=@("C:\Program Files\Itasca","D:\Program Files\Itasca","C:\Itasca","D:\Itasca"); $hits=@(); foreach($r in $roots){ if(Test-Path $r){ Get-ChildItem -Path $r -Directory -ErrorAction SilentlyContinue | ForEach-Object { $exeDir=Join-Path $_.FullName "exe64"; if(Test-Path $exeDir){ Get-ChildItem -Path $exeDir -Filter "pfc*_gui.exe" -File -ErrorAction SilentlyContinue | ForEach-Object { $hits += [PSCustomObject]@{ pfc_path=$_.Directory.Parent.FullName; gui_exe=$_.FullName } } } } } }; $hits | Sort-Object gui_exe -Unique | Select-Object -First 5 }'
```

### 2.2 Optional registry lookup (fallback)

Some installations are not registered in Windows uninstall keys; treat this as optional.

```powershell
$keys=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*');
$hits=@();
foreach($k in $keys){
  Get-ItemProperty $k -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -match 'PFC|Itasca' } |
    ForEach-Object {
      if($_.InstallLocation){
        $exeDir=Join-Path $_.InstallLocation 'exe64';
        Get-ChildItem -Path $exeDir -Filter 'pfc*_gui.exe' -File -ErrorAction SilentlyContinue | ForEach-Object {
          $exe=$_.FullName;
          $hits += [PSCustomObject]@{ pfc_path=$_.Directory.Parent.FullName; gui_exe=$exe }
        }
      }
    }
}
$hits | Sort-Object gui_exe -Unique | Select-Object -First 5
```

If still unresolved, ask user to provide exact `pfc_path`.

## Step 3 - Install/Upgrade Bridge in PFC Python

[AGENT]

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

[AGENT]

If PFC GUI is not open yet, start it from terminal (do not rely on command exit code to infer startup success):

```bash
powershell -NoProfile -Command "$gui=Get-ChildItem '{pfc_path}/exe64' -Filter 'pfc*_gui.exe' -File -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName; if(-not $gui){ throw 'No pfc*_gui.exe found under exe64' }; Start-Process $gui"
```

Confirm PFC process is running:

```bash
powershell -NoProfile -Command "tasklist | findstr /I pfc"
```

[USER ACTION REQUIRED]
In PFC GUI Python console:

```python
import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

Expected output includes:

- `PFC Bridge Server`
- `ws://localhost:9001`
- `Bridge started in non-blocking mode`

## Step 4.5 - Restart MCP Client Session (First-Time Setup)

[USER ACTION REQUIRED]

⚠️ If this is first-time MCP setup for the current workspace, fully restart your client/session now before verification (Claude Code / Codex / OpenCode).

## Step 5 - Verify from MCP Client

[AGENT]

Then reconnect MCP client and call:

- `pfc_list_tasks`

Success example (shape may vary by client):

```json
{
  "status": "success",
  "data": []
}
```

If call succeeds, setup is complete.

## Troubleshooting

- `Connection refused`:
  - Bridge not running in PFC GUI, or port `9001` not available.
- `No module named pfc_mcp_bridge`:
  - Bridge package not installed in PFC embedded Python.
- `No module named websockets`:
  - Install `websockets==9.1` in PFC embedded Python.
- `status remains pending / plot diagnostic timeout during solve`:
  - Upgrade to `pfc-mcp-bridge >= 0.1.2`.
- `pip` upgrade warning after install:
  - Usually safe to ignore if package install completed successfully.
- Need to confirm GUI process from terminal:
  - Run `powershell -NoProfile -Command "tasklist | findstr /I pfc"`.
