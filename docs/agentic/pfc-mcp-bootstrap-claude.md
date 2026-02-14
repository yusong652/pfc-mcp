# pfc-mcp Bootstrap (Claude Code)

Use this profile when the client uses `.mcp.json` style MCP config.

For Codex, use `docs/agentic/pfc-mcp-bootstrap-codex.md` instead.

## Step 1 (Claude Code) - Configure MCP

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

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/pfc-mcp-bootstrap.md`
