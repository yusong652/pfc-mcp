# -*- coding: utf-8 -*-
"""
PFC WebSocket Server Configuration Example

Copy this file to config.py and modify as needed.

Python 3.6 compatible.
"""

# WebSocket Server Configuration
WEBSOCKET_HOST = "localhost"  # Server host address
WEBSOCKET_PORT = 9001        # Server port number

# Ping Configuration (Long Timeout for Long-Running Tasks)
# These values are configured to prevent disconnection during long-running
# PFC commands like "model cycle 10000"

PING_INTERVAL = 120  # Interval between ping frames (seconds)
                     # Default: 120s (2 minutes)
                     # Longer interval to accommodate long-running commands

PING_TIMEOUT = 300   # Timeout for pong response (seconds)
                     # Default: 300s (5 minutes)
                     # Longer timeout to prevent disconnection during long tasks

# Task Processing Configuration
AUTO_START_TASK_LOOP = True  # Automatically start continuous task loop on startup
                             # Default: True (automatic processing)
                             # Set to False to use IPython hook mode only

# Notes:
# - PING_INTERVAL: How often server sends ping to check client alive
#   Longer interval (120s) means less overhead during long commands
#
# - PING_TIMEOUT: How long to wait for pong response before disconnecting
#   Longer timeout (300s) prevents disconnection when main thread is busy
#   executing commands like "model solve" or "contact cmat default"
#
# - These values work together: even if main thread is blocked for 4 minutes
#   executing a command, connection will stay alive (< 5 minute timeout)
#
# - AUTO_START_TASK_LOOP: When True, automatically starts continuous task
#   processing loop after server startup, providing immediate command processing
#   without manual triggering. When False, uses IPython hook mode only.
