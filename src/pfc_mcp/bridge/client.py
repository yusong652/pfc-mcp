"""WebSocket client for communicating with the PFC bridge server."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from uuid import uuid4

import websockets

from pfc_mcp.config import get_bridge_config

logger = logging.getLogger("pfc-mcp.bridge")


class PFCBridgeClient:
    """Async request/response client for pfc-bridge WebSocket protocol."""

    def __init__(
        self,
        url: str,
        reconnect_interval_s: float,
        max_retries: int,
        request_timeout_s: float,
        auto_reconnect: bool,
    ) -> None:
        self.url = url
        self.reconnect_interval_s = reconnect_interval_s
        self.max_retries = max_retries
        self.request_timeout_s = request_timeout_s
        self.auto_reconnect = auto_reconnect

        self._websocket: Any | None = None
        self._receiver_task: asyncio.Task[Any] | None = None
        self._pending_requests: Dict[str, asyncio.Future[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._websocket is not None

    async def connect(self) -> None:
        async with self._lock:
            if self._websocket is not None:
                return
            self._websocket = await websockets.connect(self.url, compression=None)
            self._receiver_task = asyncio.create_task(self._receive_loop())
            logger.info("Connected to pfc-bridge at %s", self.url)

    async def disconnect(self) -> None:
        async with self._lock:
            receiver_task = self._receiver_task
            websocket = self._websocket
            self._receiver_task = None
            self._websocket = None

        if receiver_task is not None:
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

        if websocket is not None:
            try:
                await websocket.close()
            except Exception:
                pass

        self._fail_pending(ConnectionError("Connection closed"))

    async def _ensure_connected(self) -> None:
        if self.connected:
            return
        await self.connect()

    def _fail_pending(self, exc: Exception) -> None:
        pending = list(self._pending_requests.values())
        self._pending_requests.clear()
        for future in pending:
            if not future.done():
                future.set_exception(exc)

    async def _receive_loop(self) -> None:
        assert self._websocket is not None
        try:
            async for raw_message in self._websocket:
                payload = json.loads(raw_message)
                msg_type = payload.get("type")
                if msg_type not in {"result", "diagnostic_result"}:
                    continue
                request_id = payload.get("request_id")
                if not request_id:
                    continue
                future = self._pending_requests.pop(request_id, None)
                if future and not future.done():
                    future.set_result(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Bridge receive loop stopped: %s", exc)
        finally:
            async with self._lock:
                self._websocket = None
                self._receiver_task = None
            self._fail_pending(ConnectionError("Bridge connection lost"))

    async def _send_request(self, message: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
        await self._ensure_connected()
        assert self._websocket is not None

        request_id = message.get("request_id") or str(uuid4())
        message["request_id"] = request_id

        loop = asyncio.get_event_loop()
        future: asyncio.Future[Dict[str, Any]] = loop.create_future()
        self._pending_requests[request_id] = future

        try:
            await self._websocket.send(json.dumps(message))
            return await asyncio.wait_for(future, timeout=timeout_s)
        except asyncio.TimeoutError as exc:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Bridge request timed out after {timeout_s:.1f}s") from exc

    async def _request_with_retry(
        self,
        message: Dict[str, Any],
        operation_name: str,
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        timeout = timeout_s if timeout_s is not None else self.request_timeout_s
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                return await self._send_request(message, timeout)
            except Exception as exc:
                last_error = exc
                await self.disconnect()
                if not self.auto_reconnect or attempt >= attempts:
                    break
                await asyncio.sleep(self.reconnect_interval_s)

        assert last_error is not None
        raise ConnectionError(f"{operation_name} failed: {last_error}") from last_error

    async def execute_task(
        self,
        script_path: str,
        description: str,
        task_id: str,
        session_id: str,
        timeout_ms: Optional[int],
        run_in_background: bool,
        source: str = "agent",
    ) -> Dict[str, Any]:
        timeout_s = 10.0 if run_in_background else max(self.request_timeout_s, (timeout_ms or 30000) / 1000.0 + 5.0)
        return await self._request_with_retry(
            {
                "type": "pfc_task",
                "task_id": task_id,
                "session_id": session_id,
                "script_path": script_path,
                "description": description,
                "timeout_ms": timeout_ms,
                "run_in_background": run_in_background,
                "source": source,
            },
            operation_name="pfc_task",
            timeout_s=timeout_s,
        )

    async def check_task_status(self, task_id: str) -> Dict[str, Any]:
        return await self._request_with_retry(
            {"type": "check_task_status", "task_id": task_id},
            operation_name="check_task_status",
        )

    async def execute_diagnostic(self, script_path: str, timeout_ms: int = 30000) -> Dict[str, Any]:
        timeout_s = max(self.request_timeout_s, timeout_ms / 1000.0 + 5.0)
        return await self._request_with_retry(
            {
                "type": "diagnostic_execute",
                "script_path": script_path,
                "timeout_ms": timeout_ms,
            },
            operation_name="diagnostic_execute",
            timeout_s=timeout_s,
        )

    async def list_tasks(self, session_id: Optional[str], offset: int, limit: Optional[int]) -> Dict[str, Any]:
        return await self._request_with_retry(
            {
                "type": "list_tasks",
                "session_id": session_id,
                "offset": offset,
                "limit": limit,
            },
            operation_name="list_tasks",
        )

    async def interrupt_task(self, task_id: str) -> Dict[str, Any]:
        return await self._request_with_retry(
            {"type": "interrupt_task", "task_id": task_id},
            operation_name="interrupt_task",
            timeout_s=5.0,
        )

    async def get_working_directory(self) -> Optional[str]:
        response = await self._request_with_retry(
            {"type": "get_working_directory"},
            operation_name="get_working_directory",
        )
        if response.get("status") != "success":
            return None
        data = response.get("data") or {}
        return data.get("working_directory")


_client: PFCBridgeClient | None = None
_client_lock = asyncio.Lock()


async def get_bridge_client() -> PFCBridgeClient:
    """Return the global bridge client instance with lazy initialization."""
    global _client
    async with _client_lock:
        if _client is None:
            config = get_bridge_config()
            _client = PFCBridgeClient(
                url=config.url,
                reconnect_interval_s=config.reconnect_interval_s,
                max_retries=config.max_retries,
                request_timeout_s=config.request_timeout_s,
                auto_reconnect=config.auto_reconnect,
            )
        await _client.connect()
        return _client


async def close_bridge_client() -> None:
    """Close global bridge client connection."""
    global _client
    async with _client_lock:
        if _client is None:
            return
        client = _client
        _client = None
    await client.disconnect()
