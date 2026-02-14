# -*- coding: utf-8 -*-
"""
PFC Bridge Startup Script (legacy compatibility wrapper).

Prefer:
    import pfc_mcp_bridge
    pfc_mcp_bridge.start()

This script is kept for backward compatibility with:
    %run /path/to/pfc-mcp/pfc-bridge/start_bridge.py
"""

import os
import sys


def _ensure_local_src_on_path():
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


_ensure_local_src_on_path()

import pfc_mcp_bridge  # type: ignore  # noqa: E402


def main():
    pfc_mcp_bridge.start()


if __name__ == "__main__":
    main()
