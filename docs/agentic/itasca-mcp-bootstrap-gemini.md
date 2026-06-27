# itasca-mcp Bootstrap (Gemini CLI)

Use this profile when the client is Gemini CLI.

## Step 1 (Gemini CLI) - Configure MCP

[AGENT]

**Primary (CLI, user scope):**

```bash
gemini mcp add --scope user itasca-mcp uvx itasca-mcp
```

`--scope user` is REQUIRED. Without it the default scope is `project` (writes only `./.gemini/settings.json`), which reintroduces the "switch working directory → tool disappears" footgun. Requires Gemini CLI >= v0.36; if `mcp add` or the flag is missing, run `gemini mcp add --help` to confirm, then use the fallback.

**Fallback (edit user config file):** `~/.gemini/settings.json` — Windows: `%USERPROFILE%\.gemini\settings.json`. Gemini resolves the home directory directly (no `XDG_*`, no `%APPDATA%`). Add/merge this entry under the top-level `mcpServers` key (command and args must be split):

```json
{
  "mcpServers": {
    "itasca-mcp": {
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
      "command": "uv",
      "args": ["tool", "run", "itasca-mcp"]
    }
  }
}
```

Last resort: if the user config file itself is unavailable or write-blocked, use a workspace-level `.gemini/settings.json` with the same entry — accepting it will not survive a working-directory change.

[USER ACTION REQUIRED]

Always close and reopen Gemini CLI session before continuing.

Then continue to Step 2 and verify with `itasca_list_tasks` at the end of bootstrap.

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/itasca-mcp-bootstrap.md`
