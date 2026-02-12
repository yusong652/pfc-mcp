# -*- coding: utf-8 -*-
"""
PFC Bridge Startup Script (legacy compatibility wrapper).

Prefer:
    import pfc_mcp_bridge
    pfc_mcp_bridge.start()

This script is kept for backward compatibility with:
    %run /path/to/pfc-mcp/pfc-bridge/start_bridge.py
"""

import sys
import os

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import pfc_mcp_bridge

pfc_mcp_bridge.start()
