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

Use the client-specific Step 1 profile:

- OpenCode: https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap-opencode.md
- Claude Code: https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap-claude.md
- Codex: https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap-codex.md
- Gemini CLI: https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap-gemini.md
- toyoura-nagisa: https://raw.githubusercontent.com/yusong652/pfc-mcp/main/docs/agentic/pfc-mcp-bootstrap-toyoura-nagisa.md

If raw URL fetch is unavailable, use repository-relative paths:

- `docs/agentic/pfc-mcp-bootstrap-opencode.md`
- `docs/agentic/pfc-mcp-bootstrap-claude.md`
- `docs/agentic/pfc-mcp-bootstrap-codex.md`
- `docs/agentic/pfc-mcp-bootstrap-gemini.md`
- `docs/agentic/pfc-mcp-bootstrap-toyoura-nagisa.md`

Apply this MCP launch contract in your client's native config format:

- server id/name: `pfc-mcp`
- primary launch command: `uvx pfc-mcp`
- fallback launch command: `uv tool run pfc-mcp`
- enable server in client config
- prefer workspace-level config by default; use global config only if user explicitly requests it

When editing MCP config, use this order:

1. If config file does not exist, create it.
2. If config exists but has no `pfc-mcp` entry, merge/add only that entry.
3. If `pfc-mcp` already exists, validate/update only MCP launch fields (`command`, `args`, and client-specific extras).
4. Do not overwrite unrelated MCP servers.

## Step 2 - Resolve `pfc_path`

[AGENT]

`pfc_path` should be the PFC install directory containing `exe64/pfc*_gui.exe`.

### 2.0 Quick probe (fast path)

Try lightweight checks first:

```bash
ls "C:/Program Files/Itasca"
ls "D:/Program Files/Itasca"
```

If obvious install folders are found, immediately drill into those folders and check `exe64/pfc*_gui.exe` before running the full PowerShell lookup.

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

PowerShell form (recommended on Windows shells):

```powershell
& "{pfc_path}/exe64/python36/python.exe" -m pip show pfc-mcp-bridge
```

Install/upgrade to required version:

```bash
"{pfc_path}/exe64/python36/python.exe" -m pip install --user --upgrade pfc-mcp-bridge
```

PowerShell form (recommended on Windows shells):

```powershell
& "{pfc_path}/exe64/python36/python.exe" -m pip install --user --upgrade pfc-mcp-bridge
```

Verify import and version:

```bash
"{pfc_path}/exe64/python36/python.exe" -c "import pfc_mcp_bridge; print(pfc_mcp_bridge.__version__)"
```

PowerShell form (recommended on Windows shells):

```powershell
& "{pfc_path}/exe64/python36/python.exe" -c "import pfc_mcp_bridge; print(pfc_mcp_bridge.__version__)"
```

Ignore pip upgrade warnings in this environment. PFC embedded Python 3.6 commonly uses older pip.

If websocket dependency errors appear, install:

```bash
"{pfc_path}/exe64/python36/python.exe" -m pip install --user websockets==9.1
```

PowerShell form (recommended on Windows shells):

```powershell
& "{pfc_path}/exe64/python36/python.exe" -m pip install --user websockets==9.1
```

## Step 4 - Start Bridge in PFC GUI

[AGENT]

If PFC GUI is not open yet, start it from terminal (do not rely on command exit code to infer startup success):

```bash
powershell -NoProfile -Command "$gui=Get-ChildItem '{pfc_path}/exe64' -Filter 'pfc*_gui.exe' -File -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName; if(-not $gui){ throw 'No pfc*_gui.exe found under exe64' }; Start-Process $gui"
```

Confirm PFC process is running:

```bash
powershell -NoProfile -Command "$procs=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^pfc(2d|3d)\\d+_gui\\.exe$' }; if($procs){$procs | Select-Object Name,ProcessId | Format-Table -AutoSize} else {Write-Output 'No PFC GUI process found'}"
```

If both `pfc2d*_gui.exe` and `pfc3d*_gui.exe` are available and user did not specify, prefer 3D (`pfc3d`) by default.

[USER ACTION REQUIRED]

Complete these in order:

1) In PFC GUI Python console:

```python
import pfc_mcp_bridge
pfc_mcp_bridge.start()
```

2) Restart client session now (close and reopen) before Step 5 verification.

Expected output includes:

- `PFC Bridge Server`
- `ws://localhost:9001`
- `Bridge started in non-blocking mode`

## Step 5 - Verify from MCP Client

[AGENT]

Then reconnect MCP client and call:

- `pfc_list_tasks`

If `pfc_*` MCP tools are not visible in the client, ask user to fully restart client session first, then retry.

Success example (shape may vary by client):

```json
{
  "status": "success",
  "data": []
}
```

`status: success` means verification passed. `data` can be empty or contain existing tasks, both are normal.

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
  - Run the exact GUI filter command from Step 4 (matches `pfc2d*_gui.exe` / `pfc3d*_gui.exe`).
- `pfc_*` tools missing in client after setup:
  - Client session was not fully restarted after Step 1. Close/reopen client session and retry Step 5.
- PowerShell error `Unexpected token '-m'`:
  - Quoted executable path was not invoked with `&`. Use `& "{pfc_path}/exe64/python36/python.exe" -m ...`.
