# -*- coding: utf-8 -*-
"""
PFC Bridge Startup Script

Runs WebSocket server in background thread while keeping IPython interactive.
Commands execute in main thread via queue for thread safety.

Usage (PFC IPython):
    # replace /path/to/pfc-mcp with your pfc-mcp root path
    %run /path/to/pfc-mcp/pfc-bridge/start_bridge.py

Tip: use forward slashes and avoid wrapping the path with extra quotes.
"""

import sys
import os
import asyncio
import logging
import threading
import time

# ── Configuration ──────────────────────────────────────────
HOST = "localhost"
PORT = 9001
PING_INTERVAL = 120   # seconds between ping frames
PING_TIMEOUT = 300    # seconds to wait for pong before disconnect

# Add script directory to sys.path so `from server.xxx import ...` works
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# Configure logging to .pfc-bridge/bridge.log in workspace
bridge_dir = os.path.join(os.getcwd(), ".pfc-bridge")
if not os.path.exists(bridge_dir):
    os.makedirs(bridge_dir)
log_file = os.path.join(bridge_dir, "bridge.log")

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers.clear()

formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
for handler in [logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file, mode='w', encoding='utf-8')]:
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

# Import server components
from server.execution import MainThreadExecutor
from server.server import create_server

# Track initialization status for summary
_init_status = {
    "pfc_state": False,
    "interrupt": False,
    "diagnostic": False,
}

# Create main thread executor and stop event
main_executor = MainThreadExecutor()
stop_event = threading.Event()

# Configure PFC Python state and register callbacks
try:
    import itasca as it  # type: ignore
    it.command("python-reset-state false")
    _init_status["pfc_state"] = True

    from server.signals import register_interrupt_callback, register_diagnostic_callback
    _init_status["interrupt"] = register_interrupt_callback(it, position=50.0)
    _init_status["diagnostic"] = register_diagnostic_callback(it, position=51.0)
except ImportError:
    pass
except Exception as e:
    logging.warning("Failed to configure PFC: {}".format(e))

# Create and start server
pfc_server = create_server(main_executor=main_executor, host=HOST, port=PORT,
                           ping_interval=PING_INTERVAL, ping_timeout=PING_TIMEOUT)

def run_server_background():
    """Run WebSocket server in background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(pfc_server.start())
        loop.run_forever()
    except Exception as e:
        logging.error("Server error: {}".format(e))
        import traceback
        traceback.print_exc()
    finally:
        loop.close()

server_thread = threading.Thread(target=run_server_background, daemon=True)
server_thread.start()
time.sleep(0.5)

# Utility functions
def run_task_loop(interval=0.01):
    """Run continuous task processing loop. Press Ctrl+C to stop."""
    print("Task loop running (Ctrl+C to stop)...")
    stop_event.clear()
    try:
        while not stop_event.is_set():
            main_executor.process_tasks()
            stop_event.wait(interval)
    except KeyboardInterrupt:
        print("\nLoop stopped")
    finally:
        stop_event.clear()

def server_status():
    """Display server status."""
    features = [name for name, ok in [
        ("PFC", _init_status["pfc_state"]),
        ("Interrupt", _init_status["interrupt"]),
        ("Diagnostic", _init_status["diagnostic"]),
    ] if ok]

    print("\n" + "=" * 60)
    print("PFC Bridge Server")
    print("=" * 60)
    print("  URL:         ws://{}:{}".format(HOST, PORT))
    print("  Log:         {}".format(log_file))
    print("  Running:     {}".format(server_thread.is_alive()))
    print("  Connections: {}".format(len(pfc_server.active_connections)))
    print("  Queue:       {} pending".format(main_executor.queue_size()))
    if features:
        print("  Features:    {}".format(", ".join(features)))
    if not _init_status["pfc_state"]:
        print("  [!] itasca module not available")
    print("=" * 60 + "\n")

# ── Startup ───────────────────────────────────────────────
server_status()
print("Task loop will now start on the main thread.")
print("There may be brief initial lag, but WebSocket")
print("requests are accepted immediately.")
input("\nPress Enter to start task loop...")
run_task_loop()
