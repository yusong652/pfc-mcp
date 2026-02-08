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

# Add script directory to sys.path
try:
    import server
except ImportError:
    _script_dir = None
    if '__file__' in dir():
        _script_dir = os.path.dirname(os.path.abspath(__file__))

    if not _script_dir:
        try:
            import itasca as it
            _script_dir = it.fish.get('_pfc_bridge_path') or it.fish.get('_pfc_server_path')
        except:
            pass

    if _script_dir and _script_dir not in sys.path:
        sys.path.insert(0, _script_dir)

# Configure logging to .nagisa/server.log
nagisa_dir = os.path.join(os.getcwd(), ".nagisa")
if not os.path.exists(nagisa_dir):
    os.makedirs(nagisa_dir)
log_file = os.path.join(nagisa_dir, "server.log")

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

# Load configuration with fallback to defaults
try:
    from config import WEBSOCKET_HOST as HOST, WEBSOCKET_PORT as PORT, \
                       PING_INTERVAL as PING_INT, PING_TIMEOUT as PING_TO, \
                       AUTO_START_TASK_LOOP as AUTO_START  # type: ignore
    _config_loaded = True
except ImportError:
    HOST, PORT, PING_INT, PING_TO, AUTO_START = "localhost", 9001, 120, 300, True
    _config_loaded = False

# Track initialization status for summary
_init_status = {
    "config": _config_loaded,
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
                           ping_interval=PING_INT, ping_timeout=PING_TO)

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

# Register IPython hook for auto task processing
try:
    from IPython import get_ipython  # type: ignore
    ip = get_ipython()
    if ip:
        ip.events.register('post_execute', main_executor.process_tasks)
        processing_mode = "hook"
    else:
        processing_mode = "manual"
except ImportError:
    processing_mode = "manual"

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

def get_queue_size():
    """Get current task queue size."""
    return main_executor.queue_size()

def stop_task_loop():
    """Stop the running task loop gracefully."""
    if stop_event.is_set():
        print("Task loop is not running or already stopping")
    else:
        print("Stopping task loop...")
        stop_event.set()

def server_status():
    """Display server status and usage information."""
    print("\n" + "=" * 60)
    print("PFC Bridge Server")
    print("=" * 60)
    print("  URL:         ws://{}:{}".format(HOST, PORT))
    print("  Running:     {}".format(server_thread.is_alive()))
    print("  Connections: {}".format(len(pfc_server.active_connections)))
    print("  Queue:       {} pending".format(main_executor.queue_size()))
    print("  Mode:        {}".format(processing_mode))
    print("-" * 60)
    print("Commands:")
    print("  server_status()   - Show this status")
    print("  run_task_loop()   - Continuous processing (Ctrl+C to stop)")
    print("=" * 60 + "\n")

# Startup summary
def _print_startup_summary():
    """Print startup summary with status indicators."""
    print("\n" + "=" * 60)
    print("PFC Bridge Server")
    print("=" * 60)
    print("  URL:       ws://{}:{}".format(HOST, PORT))
    print("  Log:       {}".format(log_file))

    # Feature status
    features = [name for name, enabled in [
        ("PFC", _init_status["pfc_state"]),
        ("Interrupt", _init_status["interrupt"]),
        ("Diagnostic", _init_status["diagnostic"]),
    ] if enabled]
    if features:
        print("  Features:  {}".format(", ".join(features)))

    # Warnings
    warnings = []
    if not _init_status["config"]:
        warnings.append("config.py not found (using defaults)")
    if not _init_status["pfc_state"]:
        warnings.append("itasca module not available")

    if warnings:
        print("-" * 60)
        for w in warnings:
            print("  [!] {}".format(w))

    print("-" * 60)
    print("Commands:  server_status()  run_task_loop()")
    print("=" * 60 + "\n")

_print_startup_summary()

# Auto-start task loop if enabled
if AUTO_START and processing_mode == "hook":
    print("Auto-starting task loop... (Ctrl+C to stop)")
    time.sleep(0.5)
    run_task_loop()
