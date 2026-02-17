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

    def get_current_output(self):
        # type: () -> Optional[str]
        """Get current output from log file.

        For active tasks, flushes the write buffer first to ensure
        all data is on disk before reading.
        """
        # Flush active write buffer to disk
        if self.output_buffer:
            try:
                self.output_buffer.flush()
            except Exception:
                pass

        # Read from log file
        if self.log_path:
            try:
                if os.path.exists(self.log_path):
                    with open(self.log_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                logger.warning("Failed to read log file: {}".format(e))

        # Backward compatibility: old persisted format with inline output
        snapshot = getattr(self, '_output_snapshot', None)
        return snapshot if snapshot else None

    def _create_data_builder(self):
        # type: () -> TaskDataBuilder
        """Create pre-configured TaskDataBuilder with common fields."""
        return TaskDataBuilder(
            self.task_id, "script",
            self.script_name, self.entry_script, self.description
        )

    def get_status_response(self):
        # type: () -> Dict[str, Any]
        """Get task status response with output and timing."""
        current_status = self.status
        elapsed_time = self.get_elapsed_time()

        if current_status == "pending":
            return self._build_pending_response(elapsed_time)
        elif current_status == "running":
            return self._build_running_response(elapsed_time)
        elif current_status == "completed":
            return self._build_completed_response(elapsed_time)
        elif current_status == "interrupted":
            return self._build_interrupted_response(elapsed_time)
        else:  # failed
            return self._build_failed_response(elapsed_time)

    def _build_pending_response(self, elapsed_time):
        # type: (float) -> Dict[str, Any]
        current_output = self.get_current_output()

        data = (self._create_data_builder()
            .with_timing(self.start_time, elapsed_time=elapsed_time)
            .with_output(current_output)
            .build())

        message = "Script queued (waiting for main thread): {}\nWaiting time: {:.2f}s".format(
            self.description, elapsed_time
        )

        return build_response("pending", message, data)

    def _build_running_response(self, elapsed_time):
        # type: (float) -> Dict[str, Any]
        current_output = self.get_current_output()

        data = (self._create_data_builder()
            .with_timing(self.start_time, elapsed_time=elapsed_time)
            .with_output(current_output)
            .build())

        message = "Script executing: {}\nElapsed time: {:.2f}s".format(
            self.description, elapsed_time
        )

        return build_response("running", message, data)

    def _build_completed_response(self, elapsed_time):
        # type: (float) -> Dict[str, Any]
        output_text = self.get_current_output()

        # Extract result from future (active tasks only)
        result_data = None
        result_status = "success"
        if self.future:
            try:
                result = self.future.result(timeout=0)
                if isinstance(result, dict):
                    result_data = result.get("result")
                    result_status = result.get("status", "success")
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
            .with_output(output_text if output_text else "")
            .with_result(serialized_result)
            .build())

        return build_response(result_status, message, data)

    def _build_interrupted_response(self, elapsed_time):
        # type: (float) -> Dict[str, Any]
        output_text = self.get_current_output()

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
            .with_output(output_text if output_text else "")
            .build())

        return build_response("interrupted", message, data)

    def _build_failed_response(self, elapsed_time):
        # type: (float) -> Dict[str, Any]
        output_text = self.get_current_output()
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
            .with_output(output_text if output_text else "")
            .with_error(error_msg)
            .build())

        return build_response("error", message, data)

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
