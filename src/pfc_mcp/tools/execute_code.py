"""PFC execute_code tool — synchronous code execution in PFC process."""

from typing import Any

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.contracts import build_ok
from pfc_mcp.formatting import build_bridge_error, build_operation_error, is_bridge_connectivity_error
from pfc_mcp.utils import ConsoleCode, ConsoleTimeoutSeconds


def register(mcp: FastMCP) -> None:
    """Register pfc_execute_code tool."""

    @mcp.tool()
    async def pfc_execute_code(
        code: ConsoleCode,
        timeout: ConsoleTimeoutSeconds = 10,
    ) -> dict[str, Any]:
        """Execute Python code synchronously in the running PFC process.

        Returns stdout and an optional result variable immediately.
        Code runs in the PFC main thread; side effects persist.

        Scheduling: This tool remains available whether PFC is cycling
        or idle — you can query model state while a task is running.

        Environment: PFC embedded Python 3.6.

        Typical uses:
        - Query model state: ball/wall/contact counts, current cycle
        - Create and export plots: itasca.command('plot ...')
        - Read or set properties, inspect variables
        - Development and REPL-style testing

        Unlike pfc_execute_task, this tool is fire-and-return: the
        response contains the full output. It is NOT tracked by
        pfc_list_tasks and cannot be interrupted or polled.

        WARNING: Avoid blocking calls (model.solve with many cycles,
        long loops). They block the PFC main thread until completion
        or timeout, and cannot be cancelled. Use pfc_execute_task for
        anything that may run longer than a few seconds.
        """
        try:
            client = await get_bridge_client()
            response = await client.execute_code(
                code=code,
                timeout_ms=timeout * 1000,
            )
        except Exception as exc:
            if is_bridge_connectivity_error(exc):
                return build_bridge_error(exc)
            return build_operation_error(
                "execute_code_failed",
                "Code execution failed",
                reason=str(exc),
            )

        status = response.get("status", "unknown")
        message = response.get("message", "")

        if status == "timeout":
            return build_operation_error(
                "timeout",
                "Execution timed out",
                reason=message,
                action="Reduce code complexity or increase timeout",
            )

        if status == "error":
            error = response.get("error") or {}
            return build_operation_error(
                error.get("code", "execute_code_error"),
                error.get("message", message),
                reason=message,
            )

        data = response.get("data") or {}
        result_data: dict[str, Any] = {
            "output": data.get("output") or "(no output)",
        }
        if data.get("result") is not None:
            result_data["result"] = data["result"]

        return build_ok(result_data)
