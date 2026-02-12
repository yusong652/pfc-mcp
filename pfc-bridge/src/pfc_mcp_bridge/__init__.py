"""PFC MCP Bridge - WebSocket bridge for ITASCA PFC.

Runs inside PFC GUI's Python environment and exposes the PFC SDK
as a remote WebSocket API for MCP clients and other tools.

Usage (in PFC GUI Python console):
    import pfc_mcp_bridge
    pfc_mcp_bridge.start()
"""

__version__ = "0.1.0"


def start(host="localhost", port=9001, ping_interval=120, ping_timeout=300):
    """Start the PFC Bridge server.

    Starts a WebSocket server in a background thread and runs the main-thread
    task processing loop (blocking).  Press Ctrl+C to stop.

    Args:
        host: Server host address.
        port: Server port number.
        ping_interval: Seconds between WebSocket ping frames.
        ping_timeout: Seconds to wait for pong before disconnect.
    """
    import sys
    import os
    import asyncio
    import logging
    import threading
    import time

    # ── Logging ───────────────────────────────────────────────
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

    # ── Server components ─────────────────────────────────────
    from .execution import MainThreadExecutor
    from .server import create_server

    init_status = {
        "pfc_state": False,
        "interrupt": False,
        "diagnostic": False,
    }

    main_executor = MainThreadExecutor()
    stop_event = threading.Event()

    # ── PFC configuration ─────────────────────────────────────
    try:
        import itasca as it  # type: ignore
        it.command("python-reset-state false")
        init_status["pfc_state"] = True

        from .signals import register_interrupt_callback, register_diagnostic_callback
        init_status["interrupt"] = register_interrupt_callback(it, position=50.0)
        init_status["diagnostic"] = register_diagnostic_callback(it, position=51.0)
    except ImportError:
        pass
    except Exception as e:
        logging.warning("Failed to configure PFC: {}".format(e))

    # ── Start WebSocket server ────────────────────────────────
    pfc_server = create_server(
        main_executor=main_executor, host=host, port=port,
        ping_interval=ping_interval, ping_timeout=ping_timeout,
    )

    def run_server_background():
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

    # ── Status display ────────────────────────────────────────
    features = [name for name, ok in [
        ("PFC", init_status["pfc_state"]),
        ("Interrupt", init_status["interrupt"]),
        ("Diagnostic", init_status["diagnostic"]),
    ] if ok]

    print("\n" + "=" * 60)
    print("PFC Bridge Server")
    print("=" * 60)
    print("  URL:         ws://{}:{}".format(host, port))
    print("  Log:         {}".format(log_file))
    print("  Running:     {}".format(server_thread.is_alive()))
    if features:
        print("  Features:    {}".format(", ".join(features)))
    if not init_status["pfc_state"]:
        print("  [!] itasca module not available")
    print("=" * 60 + "\n")

    # ── Main-thread task loop (blocking) ──────────────────────
    print("Task loop running (Ctrl+C to stop)...")
    stop_event.clear()
    try:
        while not stop_event.is_set():
            main_executor.process_tasks()
            stop_event.wait(0.01)
    except KeyboardInterrupt:
        print("\nLoop stopped")
    finally:
        stop_event.clear()
