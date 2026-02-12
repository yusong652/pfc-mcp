"""
Task Response Builder - Unified response data construction.

This module provides a builder pattern for constructing task response
data dictionaries, reducing code duplication across ScriptRunner and ScriptTask.

Python 3.6 compatible implementation.
"""

from typing import Any, Dict, Optional


class TaskDataBuilder:
    """
    Builder for task response data dictionaries.

    Provides a fluent interface for constructing task metadata,
    ensuring consistent field naming across all response points.

    Example:
        data = (TaskDataBuilder(task_id, "script", script_name, entry_script, description)
            .with_timing(start_time, end_time, elapsed_time)
            .with_output(output_text)
            .with_result(result)
            .build())
    """

    def __init__(
        self,
        task_id,  # type: str
        task_type,  # type: str
        script_name,  # type: str
        entry_script,  # type: str
        description,  # type: str
    ):
        # type: (...) -> None
        """
        Initialize builder with required task metadata.

        Args:
            task_id: Unique task identifier
            task_type: Task type (e.g., "script")
            script_name: Script file name (e.g., "main.py")
            entry_script: Absolute path to entry script
            description: Task description from agent
        """
        self._data = {
            "task_id": task_id,
            "task_type": task_type,
            "script_name": script_name,
            "entry_script": entry_script,
            "description": description,
        }  # type: Dict[str, Any]

    def with_session(self, session_id):
        # type: (str) -> TaskDataBuilder
        """Add session_id field."""
        self._data["session_id"] = session_id
        return self

    def with_timing(
        self,
        start_time,  # type: Optional[float]
        end_time=None,  # type: Optional[float]
        elapsed_time=None,  # type: Optional[float]
    ):
        # type: (...) -> TaskDataBuilder
        """
        Add timing information.

        Args:
            start_time: Task start timestamp
            end_time: Task end timestamp (for completed tasks)
            elapsed_time: Elapsed time in seconds
        """
        self._data["start_time"] = start_time
        if end_time is not None:
            self._data["end_time"] = end_time
        if elapsed_time is not None:
            self._data["elapsed_time"] = elapsed_time
        return self

    def with_output(self, output):
        # type: (Optional[str]) -> TaskDataBuilder
        """Add output field (captured stdout)."""
        if output is not None:
            self._data["output"] = output
        return self

    def with_result(self, result):
        # type: (Any) -> TaskDataBuilder
        """Add result field (script's result variable)."""
        self._data["result"] = result
        return self

    def with_error(self, error):
        # type: (Optional[str]) -> TaskDataBuilder
        """Add error field."""
        if error is not None:
            self._data["error"] = error
        return self

    def build(self):
        # type: () -> Dict[str, Any]
        """Return the built data dictionary."""
        return self._data.copy()


def build_response(status, message, data):
    # type: (str, str, Dict[str, Any]) -> Dict[str, Any]
    """
    Build a complete task response dictionary.

    Args:
        status: Response status ("pending", "success", "error", "interrupted")
        message: User-facing message
        data: Task data dictionary (from TaskDataBuilder)

    Returns:
        Complete response dictionary with status, message, and data fields
    """
    return {
        "status": status,
        "message": message,
        "data": data,
    }
