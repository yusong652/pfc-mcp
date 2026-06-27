# itasca-mcp Bootstrap (OpenCode)

Use this profile when the client is OpenCode.

## Step 1 (OpenCode) - Configure MCP

[AGENT]

Edit the global config file directly. Do NOT use the interactive `opencode mcp add` wizard — it is prompt-driven and cannot be agent-automated (and it only offers a scope choice inside a git repo; outside git it silently writes global).

Default target: global config file `opencode.json` under OpenCode's config dir:

- Windows: `%USERPROFILE%\.config\opencode\opencode.json` (NOT `%APPDATA%`)
- macOS / Linux: `~/.config/opencode/opencode.json`

OpenCode resolves this dir via XDG: if `XDG_CONFIG_HOME` (or `OPENCODE_CONFIG_DIR`) is set, the location changes accordingly. Before writing, confirm the resolved path on the actual machine with `opencode debug paths` (use the `config` value); if an `opencode.jsonc` already exists there, edit that instead. Fall back to workspace-level `./opencode.json` only if the global file is unavailable or write-blocked.

Add/merge this MCP entry:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "itasca-mcp": {
      "type": "local",
      "command": ["uvx", "itasca-mcp"],
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
    "itasca-mcp": {
      "type": "local",
      "command": ["uv", "tool", "run", "itasca-mcp"],
      "enabled": true
    }
  }
}
```

Optional verification:

```bash
opencode mcp list
```

Confirm `itasca-mcp` is listed and enabled.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/itasca-mcp-bootstrap.md`
