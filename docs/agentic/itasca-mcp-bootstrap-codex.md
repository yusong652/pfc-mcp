# itasca-mcp Bootstrap (Codex)

Use this profile when the client is OpenAI Codex CLI/IDE.

## Step 1 (Codex) - Configure MCP

[AGENT]

> **Codex IDE / GUI users (the common case):** The Codex IDE extension (VS Code / Cursor) and the CLI share the *same* `~/.codex/config.toml`. Configure it once — `codex mcp add` from any terminal, or by editing the file — and `itasca-mcp` is available in the GUI too; there is no separate GUI setup. In the IDE the file opens via the gear icon → Codex Settings → Open config.toml. Caveat: the IDE sometimes does not detect a newly added MCP server until you reload the window / restart Codex (openai/codex #6465, #7820).

**Primary (CLI):** `codex mcp add` writes the user-level config (`~/.codex/config.toml`, shared by all projects). There is no scope flag — it is user-scoped by design. The `--` separator is required:

```bash
codex mcp add itasca-mcp -- uvx itasca-mcp
```

If `uvx` is unavailable: `codex mcp add itasca-mcp -- uv tool run itasca-mcp`. Verify the subcommand exists with `codex mcp --help` (the `codex mcp` suite is part of the Rust-series CLI; legacy builds may lack it).

**Fallback (edit user config file):** `~/.codex/config.toml` — Windows: `%USERPROFILE%\.codex\config.toml` (OpenAI does not document the Windows path; set the `CODEX_HOME` env var to pin the directory if you need determinism). It is TOML, not JSON. A project-scoped `.codex/config.toml` also exists but is trusted-projects-only and is NOT written by `codex mcp add` — do not use it as the default. Add/merge this entry:

```toml
[mcp_servers.itasca-mcp]
command = "uvx"
args = ["itasca-mcp"]
```

If `uvx` is unavailable, fallback to:

```toml
[mcp_servers.itasca-mcp]
command = "uv"
args = ["tool", "run", "itasca-mcp"]
```

[USER ACTION REQUIRED]

Always close and reopen Codex session before continuing.

Optional verification:

- In Codex TUI: `/mcp`
- In terminal: `codex mcp --help` (and `codex mcp list` if available)

## Continue with common bootstrap

After Step 1, continue from Step 2 in:

- `docs/agentic/itasca-mcp-bootstrap.md`
