# pfc-mcp Bootstrap (OpenCode)

Use this profile when the client is OpenCode.

## Step 1 (OpenCode) - Configure MCP

[AGENT]

Default target: workspace-level config `<workspace>/opencode.json`.
Use global config `~/.config/opencode/opencode.json` only if user explicitly asks for global sharing.

Add/merge this MCP entry:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "pfc-mcp": {
      "type": "local",
      "command": ["uvx", "pfc-mcp"],
      "enabled": true
    }
  }
}
```

If `uvx` is unavailable, fallback to:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "pfc-mcp": {
      "type": "local",
      "command": ["uv", "tool", "run", "pfc-mcp"],
      "enabled": true
    }
  }
}
```

Set `mcp_config_changed = true` if file was created or modified; otherwise `false`.

Optional verification:

```bash
opencode mcp list
```

Confirm `pfc-mcp` is listed and enabled.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/pfc-mcp-bootstrap.md`
