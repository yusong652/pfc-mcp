# pfc-mcp Bootstrap (Gemini CLI)

Use this profile when the client is Gemini CLI.

## Step 1 (Gemini CLI) - Configure MCP

[AGENT]

Default target: workspace-level `.gemini/settings.json`.
Use user-level Gemini config only if the user explicitly requests global sharing.

Add/merge this MCP entry (command and args must be split):

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

If `uvx` is unavailable, fallback to:

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "command": "uv",
      "args": ["tool", "run", "pfc-mcp"]
    }
  }
}
```

Set `mcp_config_changed = true` if `.gemini/settings.json` was created or modified; otherwise `false`.

[USER ACTION REQUIRED]

If `mcp_config_changed = true`, run `/reload` in Gemini before continuing.

Optional verification:

```bash
gemini mcp list
```

Confirm `pfc-mcp` is listed as `Connected`.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/pfc-mcp-bootstrap.md`
