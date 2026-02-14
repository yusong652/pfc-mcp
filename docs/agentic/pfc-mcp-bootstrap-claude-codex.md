# pfc-mcp Bootstrap (Claude Code / Codex)

Use this profile when the client uses `.mcp.json` style MCP config.

## Step 1 (Claude/Codex) - Configure MCP

[AGENT]

Default target: workspace `.mcp.json`.
Use user-level MCP config only if user explicitly asks for global sharing.

Add/merge this MCP entry:

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

If `uvx` is unavailable, fallback to:

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

Set `mcp_config_changed = true` if file was created or modified; otherwise `false`.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/pfc-mcp-bootstrap.md`
