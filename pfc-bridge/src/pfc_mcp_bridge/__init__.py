"""PFC MCP Bridge - WebSocket bridge for ITASCA PFC.

Runs inside PFC GUI's Python environment and exposes the PFC SDK
as a remote WebSocket API for MCP clients and other tools.

Usage (in PFC GUI Python console):
    import pfc_mcp_bridge
    pfc_mcp_bridge.start()
"""

__version__ = "0.1.2"


# Keep global references to avoid Qt timer/callback garbage collection.
_qt_task_timer = None

DEFAULT_TIMER_INTERVAL_MS = 20
DEFAULT_MAX_TASKS_PER_TICK = 1


def start(
    host="localhost",
    port=9001,
    ping_interval=120,
    ping_timeout=300,
    timer_interval_ms=DEFAULT_TIMER_INTERVAL_MS,
    max_tasks_per_tick=DEFAULT_MAX_TASKS_PER_TICK,
):
    """Start the PFC Bridge server.

    Starts a WebSocket server in a background thread, then starts the main-thread
    task pump in Qt-timer mode (non-blocking).

    Args:
        host: Server host address.
        port: Server port number.
        ping_interval: Seconds between WebSocket ping frames.
        ping_timeout: Seconds to wait for pong before disconnect.
        timer_interval_ms: Qt timer interval in milliseconds.
        max_tasks_per_tick: Max queued tasks handled per timer tick.
            Set <=0 to process all pending tasks each tick.
    """
    import sys
    import os
    import asyncio
    import logging

    def _to_positive_int(value, default):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    interval_ms = _to_positive_int(timer_interval_ms, DEFAULT_TIMER_INTERVAL_MS)

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
    logger = logging.getLogger("PFC-Server")

    # ── Server components ─────────────────────────────────────
    from .execution import MainThreadExecutor
    from .server import create_server

    main_executor = MainThreadExecutor()

    def _start_qt_task_loop():
        # type: () -> tuple
        """Attach task processing to Qt event loop via QTimer."""
        global _qt_task_timer

        try:
            from PySide2 import QtCore  # type: ignore
        except Exception as e:
            return False, "PySide2 import failed: {}".format(e)

        app = QtCore.QCoreApplication.instance()
        if app is None:
            return False, "QCoreApplication.instance() is None"

        # Stop previous timer if start() is called multiple times.
        if _qt_task_timer is not None:
            try:
                _qt_task_timer.stop()
            except Exception:
                pass

        per_tick = None
        if max_tasks_per_tick is not None:
            try:
                value = int(max_tasks_per_tick)
                if value > 0:
                    per_tick = value
            except Exception:
                per_tick = 1

        def _process_tick():
            try:
                main_executor.process_tasks(max_tasks=per_tick)
            except Exception as e:
                logger.error("Task pump tick failed: {}".format(e))

        timer = QtCore.QTimer()
        timer.setInterval(interval_ms)
        timer.timeout.connect(_process_tick)
        timer.start()

        _qt_task_timer = timer
        return True, "qt_timer"

    # ── PFC configuration (required) ──────────────────────────
    try:
        import itasca as it  # type: ignore
    except ImportError as e:
        raise RuntimeError("itasca module not available; run bridge inside PFC GUI") from e

    it.command("python-reset-state false")

    from .signals import (
        register_interrupt_callback,
        register_diagnostic_callback,
        is_diagnostic_callback_registered,
    )

    interrupt_ok = register_interrupt_callback(it, position=50.0)
    diagnostic_ok = register_diagnostic_callback(it, position=51.0)
    diagnostic_registered = bool(diagnostic_ok or is_diagnostic_callback_registered())

    if not interrupt_ok:
        raise RuntimeError("Failed to register interrupt callback")
    if not diagnostic_registered:
        raise RuntimeError("Failed to register diagnostic callback")

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
            logger.error("Server error: {}".format(e))
            import traceback
            traceback.print_exc()
        finally:
            loop.close()

    import threading
    server_thread = threading.Thread(target=run_server_background, daemon=True)
    server_thread.start()

    if not server_thread.is_alive():
        raise RuntimeError("Bridge server thread failed to start")

    # ── Status display ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PFC Bridge Server")
    print("=" * 60)
    print("  URL:         ws://{}:{}".format(host, port))
    print("  Log:         {}".format(log_file))
    print("  Callbacks:   Interrupt, Diagnostic (registered)")
    print("=" * 60 + "\n")

    # ── Main-thread task loop ─────────────────────────────────
    started, detail = _start_qt_task_loop()
    if not started:
        raise RuntimeError("Qt timer startup failed: {}".format(detail))

    print("Bridge started in non-blocking mode (GUI remains responsive).")
