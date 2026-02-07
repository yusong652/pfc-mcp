"""
PFC Server - Lightweight WebSocket server for PFC GUI IPython shell.

This module provides a simple WebSocket server that can be started
directly from PFC GUI's IPython shell to enable remote command execution.

Note: This package is named 'server' (not 'pfc_server').
      The project directory 'pfc-bridge' uses kebab-case for filesystem compatibility.

Quick Start (in PFC GUI IPython shell - one-line command):
    >>> import sys; sys.path.append(r'C:\\path\\to\\pfc-mcp\\pfc-bridge'); exec(open(r'C:\\path\\to\\pfc-mcp\\pfc-bridge\\start_bridge.py', encoding='utf-8').read())
"""

__version__ = "0.1.0"

from . import server

__all__ = ["server"]
