# itasca-mcp Bootstrap (GitHub Copilot CLI)

Use this profile when the client is GitHub Copilot CLI.

## Step 1 (GitHub Copilot CLI) - Configure MCP

[AGENT]

**Primary (CLI):** `copilot mcp add` always writes the user-level config (global, all working directories). There is no scope flag — it is user-scoped by design:

```bash
copilot mcp add itasca-mcp --type local -- uvx itasca-mcp
```

If `uvx` is unavailable: `copilot mcp add itasca-mcp --type local -- uv tool run itasca-mcp`.

(The "Adding MCP servers" how-to page omits `copilot mcp add`; the CLI command reference documents it. If the subcommand is missing on the installed build, use the file fallback below — it works on any version.)

**Fallback (edit user config file):** `~/.copilot/mcp-config.json` — Windows: `%USERPROFILE%\.copilot\mcp-config.json` (the user/home dir, NOT `%APPDATA%`; `%LOCALAPPDATA%\copilot` is the cache, not config). Add/merge this entry under the top-level `mcpServers` key (note the required `"type": "local"`):

```json
{
  "mcpServers": {
    "itasca-mcp": {
      "type": "local",
      "command": "uvx",
      "args": ["itasca-mcp"]
    }
  }
}
```

If `uvx` is unavailable, fallback to:

```json
{
  "mcpServers": {
    "itasca-mcp": {
      "type": "local",
      "command": "uv",
      "args": ["tool", "run", "itasca-mcp"]
    }
  }
}
```

Last resort: if the user config file itself is unavailable or write-blocked, use a workspace-level `.mcp.json` with the same entry — accepting it will not survive a working-directory change.

[USER ACTION REQUIRED]

Always close and restart the Copilot CLI session before continuing. Exit the current session and start a new one.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/itasca-mcp-bootstrap.md`
