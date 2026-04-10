"""
Script Task - Lifecycle management for long-running PFC script execution.

This module provides the ScriptTask class that tracks task state,
captures real-time output, and generates status responses.

Supports both active tasks (with Future and FileBuffer) and
historical tasks restored from persistence (no Future/buffer).

Python 3.6 compatible implementation.
"""

import os
import time
import logging
from typing import Any, Dict, Optional

from ..utils import TaskDataBuilder, build_response

# Module logger
logger = logging.getLogger("PFC-Server")

# Default pagination window when caller does not specify one.
DEFAULT_PAGINATION_LIMIT = 64


class ScriptTask:
    """
    Task for Python script execution with real-time output capture.

    Tracks lifecycle from submission through completion, with output
    captured via FileBuffer for progress monitoring.

    Status values:
    - "pending": Task queued, waiting for main thread
    - "running": Task currently executing in main thread
    - "completed": Task finished successfully
    - "failed": Task finished with error
    - "interrupted": Task was interrupted by user
    """

    def __init__(self, task_id, future, script_name, entry_script,
                 output_buffer=None, description=None, on_status_change=None):
        # type: (str, Any, str, str, Any, Optional[str], Any) -> None
        self.task_id = task_id
        self.future = future
        self.description = description or ""
        self.script_name = script_name
        self.entry_script = entry_script  # type: str
        self.output_buffer = output_buffer
        self.start_time = time.time()
        self.end_time = None  # type: Optional[float]
        self._status = "pending"  # type: str
        self.on_status_change = on_status_change
        self.error = None  # type: Optional[str]

        # Extract log path from FileBuffer for persistence
        self.log_path = None  # type: Optional[str]
        if output_buffer and hasattr(output_buffer, 'get_path'):
            self.log_path = output_buffer.get_path()

        # Register completion callback
        future.add_done_callback(self._on_complete)

        logger.info(
            "Script task registered: %s (id=%s)",
            script_name, task_id
        )

    @classmethod
    def from_persisted(cls, task_data):
        # type: (Dict[str, Any]) -> ScriptTask
        """Create a task from persisted data (no Future or buffer)."""
        task = cls.__new__(cls)
        task.task_id = task_data["task_id"]
        task.description = task_data["description"]
        task.script_name = task_data.get("script_name", "")
        task.entry_script = task_data.get("entry_script") or task_data.get("script_path") or ""
        task._status = task_data["status"]
        task.start_time = task_data["start_time"]
        task.end_time = task_data.get("end_time")
        task.log_path = task_data.get("log_path")
        task.error = task_data.get("error")
        task.future = None
        task.output_buffer = None
        task.on_status_change = None
        # Backward compatibility: old format stored output inline in JSON
        task._output_snapshot = task_data.get("output", "")
        return task

    @property
    def status(self):
        # type: () -> str
        """Get current task status."""
        return self._status

    @status.setter
    def status(self, value):
        # type: (str) -> None
        self._status = value

    def _on_complete(self, f):
        # type: (Any) -> None
        """Callback executed when task completes (success, failure, or interruption)."""
        self.end_time = time.time()
        try:
            result = f.result(timeout=0)
            if isinstance(result, dict):
                result_status = result.get("status")
                if result_status == "error":
                    self.status = "failed"
                    self.error = result.get("message", "Task execution failed")
                elif result_status == "interrupted":
                    self.status = "interrupted"
                else:
                    self.status = "completed"
            else:
                self.status = "completed"
        except Exception as e:
            self.status = "failed"
            self.error = str(e)

        if self.on_status_change:
            try:
                self.on_status_change(self)
            except Exception as e:
                logger.warning("Status change callback failed: {}".format(e))

    def get_elapsed_time(self):
        # type: () -> float
        """Calculate elapsed time since task start."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        if self.future is None:
            return 0.0
        return time.time() - self.start_time

    def get_paginated_output(self, skip_newest=0, limit=DEFAULT_PAGINATION_LIMIT, filter_text=None):
        # type: (int, int, Optional[str]) -> tuple
        """Return (output_text, pagination_dict) paginating the task log.

        Reads the complete log file, optionally filters by substring,
        then extracts a tail-biased window: `skip_newest` lines from
        the end, then up to `limit` lines backwards from there.

        The `pagination` dict reports metadata against the *full* log
        (or the filtered view if `filter_text` is set), so callers can
        reason about whether older/newer content exists.
        """
        # Flush active write buffer to disk so the read sees it
        if self.output_buffer:
            try:
                self.output_buffer.flush()
            except Exception:
                pass

        # Read full log from disk. For multi-MB logs this is still fast
        # (<50 ms for 10 MB on SSD) and gives accurate pagination metadata.
        full = ""
        if self.log_path and os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8', errors='replace') as f:
                    full = f.read()
            except Exception as e:
                logger.warning("Failed to read log file: {}".format(e))

        # Backward compatibility: old persisted format with inline output
        if not full:
            full = getattr(self, '_output_snapshot', '') or ''

        lines = full.splitlines()
        if filter_text:
            lines = [line for line in lines if filter_text in line]

        total_lines = len(lines)
        start_idx = max(0, total_lines - limit - skip_newest)
        end_idx = max(0, total_lines - skip_newest)
        selected = lines[start_idx:end_idx]

        pagination = {
            "total_lines": total_lines,
            "line_range": "{}-{}".format(start_idx + 1, end_idx) if selected else "0-0",
            "has_older": start_idx > 0,
            "has_newer": skip_newest > 0,
        }

        text = "\n".join(selected) if selected else ""
        return text, pagination

    def _create_data_builder(self):
        # type: () -> TaskDataBuilder
        """Create pre-configured TaskDataBuilder with common fields."""
        return TaskDataBuilder(
            self.task_id, "script",
            self.script_name, self.entry_script, self.description
        )

    def get_status_response(self, skip_newest=0, limit=DEFAULT_PAGINATION_LIMIT, filter_text=None):
        # type: (int, int, Optional[str]) -> Dict[str, Any]
        """Get task status response with paginated output and timing.

        Pagination args are applied on the bridge side against the full
        log file, so `total_lines`, `has_older`, and `filter_text` all
        reflect the real on-disk state (not a pre-truncated window).
        """
        current_status = self.status
        elapsed_time = self.get_elapsed_time()
        output_text, pagination = self.get_paginated_output(
            skip_newest=skip_newest, limit=limit, filter_text=filter_text
        )

        if current_status == "pending":
            return self._build_pending_response(elapsed_time, output_text, pagination)
        elif current_status == "running":
            return self._build_running_response(elapsed_time, output_text, pagination)
        elif current_status == "completed":
            return self._build_completed_response(elapsed_time, output_text, pagination)
        elif current_status == "interrupted":
            return self._build_interrupted_response(elapsed_time, output_text, pagination)
        else:  # failed
            return self._build_failed_response(elapsed_time, output_text, pagination)

    def _build_pending_response(self, elapsed_time, output_text, pagination):
        # type: (float, str, Dict[str, Any]) -> Dict[str, Any]
        data = (self._create_data_builder()
            .with_timing(self.start_time, elapsed_time=elapsed_time)
            .with_output(output_text)
            .with_pagination(pagination)
            .build())

        message = "Script queued (waiting for main thread): {}\nWaiting time: {:.2f}s".format(
            self.description, elapsed_time
        )

        return build_response("pending", message, data)

    def _build_running_response(self, elapsed_time, output_text, pagination):
        # type: (float, str, Dict[str, Any]) -> Dict[str, Any]
        data = (self._create_data_builder()
            .with_timing(self.start_time, elapsed_time=elapsed_time)
            .with_output(output_text)
            .with_pagination(pagination)
            .build())

        message = "Script executing: {}\nElapsed time: {:.2f}s".format(
            self.description, elapsed_time
        )

        return build_response("running", message, data)

    def _build_completed_response(self, elapsed_time, output_text, pagination):
        # type: (float, str, Dict[str, Any]) -> Dict[str, Any]
        # Extract result from future (active tasks only)
        result_data = None
        if self.future:
            try:
                result = self.future.result(timeout=0)
                if isinstance(result, dict):
                    result_data = result.get("result")
                else:
                    result_data = result
            except Exception:
                pass

        serialized_result = self._serialize_result(result_data)

        if output_text:
            message = "Script execution completed: {}\nElapsed time: {:.2f}s\n\n=== Script Output ===\n{}".format(
                self.script_name, elapsed_time, output_text
            )
        elif serialized_result is not None:
            message = "Script completed: {}\nElapsed time: {:.2f}s\nResult: {}".format(
                self.description, elapsed_time, serialized_result
            )
        else:
            message = "Script completed: {}\nElapsed time: {:.2f}s".format(
                self.description, elapsed_time
            )

        data = (self._create_data_builder()
            .with_timing(self.start_time, self.end_time, elapsed_time)
            .with_output(output_text)
            .with_pagination(pagination)
            .with_result(serialized_result)
            .build())

        return build_response("completed", message, data)

    def _build_interrupted_response(self, elapsed_time, output_text, pagination):
        # type: (float, str, Dict[str, Any]) -> Dict[str, Any]
        if output_text:
            message = "Script interrupted by user: {}\nElapsed time: {:.2f}s\n\n=== Partial Output ===\n{}".format(
                self.script_name, elapsed_time, output_text
            )
        else:
            message = "Script interrupted by user: {}\nElapsed time: {:.2f}s".format(
                self.description, elapsed_time
            )

        data = (self._create_data_builder()
            .with_timing(self.start_time, self.end_time, elapsed_time)
            .with_output(output_text)
            .with_pagination(pagination)
            .build())

        return build_response("interrupted", message, data)

    def _build_failed_response(self, elapsed_time, output_text, pagination):
        # type: (float, str, Dict[str, Any]) -> Dict[str, Any]
        error_msg = self.error or "Task execution failed"

        if output_text:
            message = "Script execution failed: {}\nElapsed time: {:.2f}s\nError: {}\n\n=== Partial Output ===\n{}".format(
                self.script_name, elapsed_time, error_msg, output_text
            )
        else:
            message = "Script failed: {}\nElapsed time: {:.2f}s\nError: {}".format(
                self.description, elapsed_time, error_msg
            )

        data = (self._create_data_builder()
            .with_timing(self.start_time, self.end_time, elapsed_time)
            .with_output(output_text)
            .with_pagination(pagination)
            .with_error(error_msg)
            .build())

        return build_response("failed", message, data)

    def get_task_info(self):
        # type: () -> Dict[str, Any]
        """Get task summary for listing."""
        info = {
            "task_id": self.task_id,
            "task_type": "script",
            "description": self.description,
            "status": self.status,
            "elapsed_time": self.get_elapsed_time(),
            "start_time": self.start_time,
            "name": self.script_name,
            "entry_script": self.entry_script,
        }
        if self.status in ["completed", "failed", "interrupted"] and self.end_time is not None:
            info["end_time"] = self.end_time
        if self.status == "failed" and self.error:
            info["error"] = self.error
        return info

    @staticmethod
    def _serialize_result(result):
        # type: (Any) -> Any
        """Convert PFC objects to JSON-serializable format."""
        if result is None:
            return None
        elif isinstance(result, (str, int, float, bool)):
            return result
        elif isinstance(result, (list, tuple)):
            return [ScriptTask._serialize_result(item) for item in result]
        elif isinstance(result, dict):
            return {k: ScriptTask._serialize_result(v) for k, v in result.items()}
        else:
            return str(result)
