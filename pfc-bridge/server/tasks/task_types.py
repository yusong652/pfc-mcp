"""
Task Type Implementations - Script execution task class.

This module contains ScriptTask implementation, providing type-specific
behavior for Python script execution with real-time output capture.

Python 3.6 compatible implementation.
"""

import logging
from typing import Any, Dict, Optional

from .task_base import Task
from ..utils import TaskDataBuilder, build_response

# Module logger
logger = logging.getLogger("PFC-Server")

class ScriptTask(Task):
    """
    Task for Python script execution.

    Enhanced task type with real-time output capture via FileBuffer,
    suitable for long-running simulations with progress monitoring.
    Output is written directly to disk for complete preservation.
    """

    def __init__(self, task_id, session_id, future, script_name, entry_script, output_buffer=None, description=None, on_status_change=None):
        # type: (str, str, Any, str, str, Any, Optional[str], Any) -> None
        """
        Initialize script task.

        Args:
            task_id: Unique task identifier
            session_id: Session identifier for task isolation
            future: asyncio Future object for the task
            script_name: Name of the script file (e.g., "main.py")
            entry_script: Full path to entry script
            output_buffer: Optional FileBuffer for output capture (writes to disk)
            description: Task description from PFC agent (LLM-provided)
            on_status_change: Optional callback function(task) called when task status changes
        """
        # Use agent-provided description (default to empty string if None)
        super(ScriptTask, self).__init__(task_id, session_id, future, description or "", "script", on_status_change)
        self.script_name = script_name
        self.entry_script = entry_script  # type: str  # Entry script path
        self.output_buffer = output_buffer

        # Extract log path from FileBuffer for persistence
        self.log_path = None  # type: Optional[str]
        if output_buffer and hasattr(output_buffer, 'get_path'):
            self.log_path = output_buffer.get_path()

        logger.info(
            "Script task registered: %s (id=%s, session=%s)",
            script_name, task_id, session_id
        )

    def get_current_output(self):
        # type: () -> Optional[str]
        """Get current output from buffer (for running scripts)."""
        if self.output_buffer:
            try:
                return self.output_buffer.getvalue()
            except Exception as e:
                logger.warning("Failed to read output buffer: {}".format(e))
        return None

    def _create_data_builder(self):
        # type: () -> TaskDataBuilder
        """Create pre-configured TaskDataBuilder with common fields."""
        return (TaskDataBuilder(
                self.task_id, self.task_type,
                self.script_name, self.entry_script, self.description
            )
            .with_session(self.session_id))

    def _build_pending_response(self, elapsed_time):
        # type: (float) -> Dict[str, Any]
        """Build response for pending status."""
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
        """Build response for running status."""
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
        """Build response for completed status."""
        logger.info(
            "Task completed: %s (id=%s, time=%.2fs)",
            self.description, self.task_id, elapsed_time
        )

        # Get output from buffer (single source of truth)
        output_text = self.get_current_output()

        # Extract result from future
        result_data = None
        result_status = "success"
        try:
            result = self.future.result(timeout=0)
            if isinstance(result, dict):
                result_data = result.get("result")
                result_status = result.get("status", "success")
            else:
                result_data = result
        except Exception:
            pass

        # Serialize result data
        serialized_result = self._serialize_result(result_data)

        # Build message with output
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
        """Build response for interrupted status."""
        logger.info(
            "Script task interrupted: %s (id=%s, time=%.2fs)",
            self.description, self.task_id, elapsed_time
        )

        # Get output from buffer (single source of truth)
        output_text = self.get_current_output()

        # Build interrupted message with partial output
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
        """Build response for failed status."""
        logger.error("Script task failed: %s (id=%s)", self.description, self.task_id)

        # Get output from buffer (single source of truth)
        output_text = self.get_current_output()

        # Use error from task object (extracted in _on_complete and persisted)
        error_msg = self.error or "Task execution failed"

        # Build error message with partial output
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
        """Get script task summary for listing."""
        info = super(ScriptTask, self).get_task_info()
        info.update({
            "name": self.script_name,  # Script file name (for backward compatibility)
            "entry_script": self.entry_script,  # Entry script path
        })
        return info
