"""
PFC WebSocket Server - Lightweight server to run in PFC GUI IPython shell.

This module provides WebSocket server components for remote PFC control.
Server startup should be done via start_bridge.py script.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import websockets
from websockets.server import WebSocketServerProtocol  # type: ignore

from .execution import ScriptRunner, MainThreadExecutor
from .tasks import TaskManager
from .handlers import (
    ServerContext,
    handle_pfc_task,
    handle_check_task_status,
    handle_list_tasks,
    handle_diagnostic_execute,
    handle_get_working_directory,
    handle_ping,
    handle_interrupt_task,
)

# Module logger
logger = logging.getLogger("PFC-Server")


class PFCWebSocketServer:
    """WebSocket server for PFC script execution via main thread queue.

    Script-only workflow: All PFC operations must be executed through Python
    scripts using itasca.command(). Direct command execution is no longer supported.
    """

    def __init__(
        self,
        main_executor,  # type: MainThreadExecutor
        host="localhost",  # type: str
        port=9001,  # type: int
        ping_interval=120,  # type: int
        ping_timeout=300  # type: int
    ):
        # type: (...) -> None
        """
        Initialize WebSocket server.

        Args:
            main_executor: Main thread executor for queue-based command execution
            host: Server host address (default: "localhost")
            port: Server port number (default: 9001)
            ping_interval: Interval between ping frames in seconds (default: 120)
                Note: Longer interval (2 min) to accommodate long-running commands
            ping_timeout: Timeout for pong response in seconds (default: 300)
                Note: Longer timeout (5 min) to prevent disconnection during long tasks
        """
        self.main_executor = main_executor
        self.host = host
        self.port = port
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        task_manager = TaskManager()
        self.script_runner = ScriptRunner(main_executor, task_manager)
        self.active_connections = set()
        self.server = None

        # Create server context for handlers
        self._context = ServerContext(
            task_manager=task_manager,
            script_runner=self.script_runner,
            main_executor=self.main_executor,
        )

        # Message handlers registry (all handlers are async with unified signature)
        self._handlers = {
            "pfc_task": handle_pfc_task,
            "check_task_status": handle_check_task_status,
            "list_tasks": handle_list_tasks,
            "get_working_directory": handle_get_working_directory,
            "interrupt_task": handle_interrupt_task,
            "diagnostic_execute": handle_diagnostic_execute,
            "ping": handle_ping,
        }

    async def _send_response(
        self,
        websocket: WebSocketServerProtocol,
        response: Dict[str, Any],
        request_id: str = "unknown"
    ) -> bool:
        """
        Send response to client with connection error handling.

        Args:
            websocket: WebSocket connection instance
            response: Response dictionary to send
            request_id: Request ID for logging

        Returns:
            True if sent successfully, False if connection closed
        """
        try:
            await websocket.send(json.dumps(response))
            return True
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Cannot send result, connection closed: {request_id}")
            return False

    async def _process_message(self, websocket: WebSocketServerProtocol, message: str):
        """
        Process a single WebSocket message concurrently.

        This method is spawned as an independent task for each incoming message,
        allowing lightweight operations (ping, status queries) to complete even
        while long-running foreground tasks are executing.

        Args:
            websocket: WebSocket connection instance
            message: Raw message string to process
        """
        try:
            # Parse incoming message
            data = json.loads(message)
            msg_type = data.get("type", "pfc_task")
            request_id = data.get("request_id", "unknown")

            # Route to appropriate handler
            handler = self._handlers.get(msg_type)
            if handler:
                response = await handler(self._context, data)
                # Send response (ignore connection closed - will be handled by main loop)
                await self._send_response(websocket, response, request_id)
            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error_response = {
                "type": "error",
                "message": "Invalid JSON format",
                "error": str(e)
            }
            await self._send_response(websocket, error_response)

        except asyncio.CancelledError:
            # Task was cancelled (connection closed), silently exit
            raise

        except Exception as e:
            logger.error(f"Message handling error: {e}")
            error_response = {
                "type": "error",
                "message": "Internal server error",
                "error": str(e)
            }
            await self._send_response(websocket, error_response)

    async def handle_client(self, websocket: WebSocketServerProtocol, path: Optional[str] = None):
        """
        Handle WebSocket client connection with concurrent message processing.

        Each incoming message is processed in a separate async task, preventing
        long-running foreground tasks from blocking lightweight operations like
        ping/pong heartbeats and status queries.

        Args:
            websocket: WebSocket connection instance
            path: Request path (for websockets 9.x compatibility)
        """
        self.active_connections.add(websocket)
        pending_tasks = set()  # type: set

        try:
            async for message in websocket:
                # Spawn independent task for each message (non-blocking)
                task = asyncio.ensure_future(
                    self._process_message(websocket, message)
                )
                pending_tasks.add(task)
                task.add_done_callback(pending_tasks.discard)

        except websockets.exceptions.ConnectionClosed:
            pass  # Client disconnected normally

        finally:
            # Cancel pending response tasks (connection is closing)
            for task in pending_tasks:
                task.cancel()
            # Wait briefly for cancellations to complete
            if pending_tasks:
                await asyncio.gather(*pending_tasks, return_exceptions=True)
            self.active_connections.discard(websocket)

    async def start(self):
        """Start the WebSocket server (non-blocking)."""

        try:
            # Use websockets 9.1 compatible syntax (Python 3.6)
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout
            )

            # Note: Server is now running in the background
            # websockets.serve() automatically handles connections via the event loop
            # No need to block here - the server will continue running as long as
            # the event loop is active

        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

    async def wait_closed(self):
        """Wait for server to close (for graceful shutdown)."""
        if self.server:
            await self.server.wait_closed()


# Module-level utility function for creating server instances
def create_server(
    main_executor,  # type: MainThreadExecutor
    host="localhost",  # type: str
    port=9001,  # type: int
    ping_interval=120,  # type: int
    ping_timeout=300  # type: int
):
    # type: (...) -> PFCWebSocketServer
    """
    Create a PFC WebSocket server instance.

    Args:
        main_executor: Main thread executor for queue-based command execution
        host: Server host address (default: "localhost")
        port: Server port number (default: 9001)
        ping_interval: Interval between ping frames in seconds (default: 120)
            Note: Longer interval (2 min) to accommodate long-running commands
        ping_timeout: Timeout for pong response in seconds (default: 300)
            Note: Longer timeout (5 min) to prevent disconnection during long tasks

    Returns:
        PFCWebSocketServer: Server instance ready to be started

    Example:
        >>> from pfc_server.main_thread_executor import MainThreadExecutor
        >>> from pfc_server.server import create_server
        >>> executor = MainThreadExecutor()
        >>> server = create_server(executor, host="localhost", port=9001)
        >>> # Use with startup script
    """
    return PFCWebSocketServer(main_executor, host, port, ping_interval, ping_timeout)
