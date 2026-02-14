# pfc-mcp Bootstrap (toyoura-nagisa)

Use this profile when the client is toyoura-nagisa.

## Step 1 (toyoura-nagisa) - Configure MCP

[AGENT]

Preferred target: workspace-level `./.nagisa/mcp_servers.json`.
Use user-level `~/.nagisa/mcp_servers.json` only if the user explicitly requests global sharing.

Add/merge this entry under `mcpServers`:

```json
{
  "mcpServers": {
    "pfc-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["pfc-mcp"],
      "enabled": true,
      "description": "PFC MCP server"
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
      "args": ["tool", "run", "pfc-mcp"],
      "enabled": true,
      "description": "PFC MCP server"
    }
  }
}
```

Do not overwrite unrelated MCP servers in the same file.

[USER ACTION REQUIRED]

Always close and reopen the toyoura-nagisa session (or restart backend process) before continuing.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/pfc-mcp-bootstrap.md`
