# Changelog

All notable changes to `pfc-mcp-bridge` are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.3] - 2026-05-22

### Deprecated

**Final release.** `pfc-mcp-bridge` has been superseded by
[`itasca-mcp-bridge`](https://pypi.org/project/itasca-mcp-bridge/), a
product-neutral bridge that supports PFC and FLAC3D from one codebase.

This release exists solely to deliver a migration signal:

- Emits `DeprecationWarning` at import time so programmatic users
  (pytest, lint, CI) catch the move automatically.
- Prints a banner inside `start()` directing addon.py users to install
  `itasca-mcp-bridge` and download the new `addon.py` from the
  [`pfc-mcp`](https://github.com/yusong652/pfc-mcp) repo.

The multi-line `it.command()` deadlock fix (recognized aliases like
`import itasca as it`) ships only in `itasca-mcp-bridge 0.1.1+`, NOT
in this package.

## [0.3.2] - 2026-05-14

Adds two-layer cancellation for `execute_code` so runaway snippets
(`while True`, long `model cycle`, etc.) no longer jam the bridge until
restart. L1 sets an interrupt flag the PFC cycle callback polls; L2
async-raises `BridgeTimeout` on the registered exec thread for code that
never yields. Wire status now reports `terminated`, `interrupted`, or
`timeout` with `details.method` set to `stuck_in_c` / `flag_only` when
termination can't complete. Snippets that interleave inside a running
task's cycle gap no longer clobber the outer task's interrupt id.

Internal rename: `signals/script_executor` → `signals/cycle_executor`,
`handlers/script_executor` → `handlers/exec_strategy`; both
`execute_code` paths now share `execution/snippet.run_snippet()` and
the callback path stops round-tripping code through a temp file.

## [0.3.1] - 2026-05-14

Compatibility release shipping alongside an updated `addon.py` bootstrap that
falls back to a Tsinghua mirror when PyPI is unreachable, so PFC 6/7 users
behind corporate proxies or slow international routes can install the bridge
reliably. No code changes to the bridge package itself.
