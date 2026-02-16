"""PFC MCP Bridge - WebSocket bridge for ITASCA PFC.

Runs inside PFC GUI's Python environment and exposes the PFC SDK
as a remote WebSocket API for MCP clients and other tools.

Usage (in PFC GUI Python console):
    import pfc_mcp_bridge
    pfc_mcp_bridge.start()

Usage (in PFC console CLI):
    import pfc_mcp_bridge
    pfc_mcp_bridge.start(mode="console")
"""

__version__ = "0.1.3"


# Keep global references to avoid Qt timer/callback garbage collection.
_qt_task_timer = None

DEFAULT_TIMER_INTERVAL_MS = 20
DEFAULT_MAX_TASKS_PER_TICK = 1


def _start_qt_pump(main_executor, interval_ms, max_tasks_per_tick, logger):
    # type: (...) -> bool
    """Try to attach task processing to Qt event loop. Returns True on success."""
    global _qt_task_timer

    try:
        from PySide2 import QtCore  # type: ignore
    except Exception:
        return False

    app = QtCore.QCoreApplication.instance()
    if app is None:
        return False

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
    return True


def _run_blocking_pump(main_executor, interval_ms, max_tasks_per_tick, logger):
    # type: (...) -> None
    """Block the main thread and poll task queue. Used in console mode."""
    import time

    per_tick = None
    if max_tasks_per_tick is not None:
        try:
            value = int(max_tasks_per_tick)
            if value > 0:
                per_tick = value
        except Exception:
            per_tick = 1

    sleep_s = interval_ms / 1000.0
    try:
        while True:
            try:
                main_executor.process_tasks(max_tasks=per_tick)
            except Exception as e:
                logger.error("Task pump tick failed: {}".format(e))
            time.sleep(sleep_s)
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user")


def start(
    host="localhost",
    port=9001,
    ping_interval=120,
    ping_timeout=300,
    timer_interval_ms=DEFAULT_TIMER_INTERVAL_MS,
    max_tasks_per_tick=DEFAULT_MAX_TASKS_PER_TICK,
    mode="auto",
):
    """Start the PFC Bridge server.

    Starts a WebSocket server in a background thread, then starts the main-thread
    task pump.

    Args:
        host: Server host address.
        port: Server port number.
        ping_interval: Seconds between WebSocket ping frames.
        ping_timeout: Seconds to wait for pong before disconnect.
        timer_interval_ms: Timer/poll interval in milliseconds.
        max_tasks_per_tick: Max queued tasks handled per tick.
            Set <=0 to process all pending tasks each tick.
        mode: Task pump mode - "auto" (try Qt, fall back to blocking),
            "gui" (Qt only), or "console" (blocking only).
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

    # ── Port availability check ──────────────────────────────
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
    except OSError:
        raise RuntimeError(
            "Port {} is already in use. "
            "Another bridge may be running, or another process is using this port.\n"
            "Try: pfc_mcp_bridge.start(port={})".format(port, port + 1)
        )
    finally:
        sock.close()

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

    # ── Main-thread task pump ─────────────────────────────────
    use_qt = mode in ("auto", "gui")
    use_blocking = mode in ("auto", "console")

    if use_qt and _start_qt_pump(main_executor, interval_ms, max_tasks_per_tick, logger):
        print("Task loop running via Qt timer (interval={}ms, max_tasks_per_tick={})".format(
            interval_ms, max_tasks_per_tick))
        print("Bridge started in non-blocking mode (GUI remains responsive).")
        return

    if mode == "gui":
        raise RuntimeError("Qt is not available; cannot start in gui mode")

    if use_blocking:
        print("Task loop running via blocking poll (interval={}ms)".format(interval_ms))
        print("Bridge started in blocking mode (console). Press Ctrl+C to stop.")
        _run_blocking_pump(main_executor, interval_ms, max_tasks_per_tick, logger)
