"""
PFC Script Executor - Executes Python SDK scripts with direct API access.

This module provides script execution functionality using PFC Python SDK via
main thread queue, enabling queries and operations that return values.

Python 3.6 compatible implementation.
"""

import logging
import os
import sys
import time
import traceback
from typing import Any, Dict, Optional

from .main_thread import MainThreadExecutor
from ..utils import path_to_llm_format, FileBuffer, TaskDataBuilder, build_response, preprocess_script
from ..signals import set_current_task, clear_current_task, clear_interrupt

# Module logger
logger = logging.getLogger("PFC-Server")


class ScriptRunner:
    """Run Python scripts via PFC main thread queue."""

    def __init__(self, main_executor, task_manager):
        # type: (MainThreadExecutor, Any) -> None
        """
        Initialize executor with itasca module, main thread executor, and task manager.

        Args:
            main_executor: Main thread executor for queue-based execution
            task_manager: Task manager for long-running task tracking
        """
        self.main_executor = main_executor
        self.task_manager = task_manager

    def _execute(self, script_path, script_content, output_buffer, task_id):
        # type: (str, str, Any, str) -> Dict[str, Any]
        """
        Execute script in main thread (called via queue).

        Captures stdout during execution for progress tracking using shared buffer.
        Supports interruption via registered PFC callback.

        Args:
            script_path: Path to script (for error messages)
            script_content: Script content to execute
            output_buffer: FileBuffer for capturing stdout (shared with TaskManager)
            task_id: Task ID for interrupt checking

        Returns:
            Result dictionary with status, message, result, and output:
                - status: "success", "error", or "interrupted"
                - message: User-friendly message
                - result: Script result (from 'result' variable)
                - output: Captured stdout content (print statements)
        """
        # Mark task as running
        task = self.task_manager.tasks.get(task_id)
        if task:
            task.status = "running"

        # Use shared output buffer for stdout capture
        old_stdout = sys.stdout
        sys.stdout = output_buffer

        # Set current task for interrupt callback
        set_current_task(task_id)

        try:
            # Use IPython's global namespace for persistent state across scripts
            # This enables:
            # - Variables persist between script executions
            # - Imports are reused (no repeated import overhead)
            # - if __name__ == "__main__": works correctly
            # - Scripts share state with IPython Console
            import __main__

            exec_globals = __main__.__dict__

            # Set __file__ to current script path (updates each execution)
            exec_globals["__file__"] = script_path

            # Prevent stale result leakage across script runs.
            # `result` is a reserved output channel for task return payloads,
            # so each execution should start with a clean value.
            exec_globals.pop("result", None)

            # Split multi-line itasca.command() calls into individual calls
            # to prevent GIL being held for the entire batch.
            script_content = preprocess_script(script_content)

            # Try to execute as expression first (single line, returns value)
            try:
                # Use compile() with script_path for better traceback
                code_obj = compile(script_content, script_path, "eval")
                result = eval(code_obj, exec_globals, exec_globals)
            except SyntaxError:
                # If eval fails, try exec (multi-line script)
                # Use compile() with script_path to show actual file path in traceback
                code_obj = compile(script_content, script_path, "exec")
                exec(code_obj, exec_globals, exec_globals)
                # Look for 'result' variable in global namespace
                result = exec_globals.get("result", None)

            # Get captured output from shared buffer
            output_text = output_buffer.getvalue()

            # Serialize result for response
            serialized_result = self._serialize_result(result)

            # Build message with result
            script_name = os.path.basename(script_path)
            if serialized_result is not None:
                message = "Script executed: {}\nResult: {}".format(script_name, serialized_result)
            else:
                message = "Script executed: {}".format(script_name)

            return {
                "status": "success",
                "message": message,
                "result": serialized_result,
                "output": output_text,  # Include captured output
            }

        except InterruptedError as e:
            # Task was interrupted by user via callback (direct raise)
            output_text = output_buffer.getvalue()
            logger.info("Script interrupted: {} - {}".format(script_path, str(e)))

            return {
                "status": "interrupted",
                "message": "Script interrupted by user: {}".format(str(e)),
                "result": None,
                "output": output_text,  # Include output up to interruption point
            }

        except BaseException as e:
            # Use BaseException to catch ALL exceptions including those from C extensions
            # Get captured output even on error
            output_text = output_buffer.getvalue()

            # Check if this is a wrapped InterruptedError from our callback
            # PFC wraps callback exceptions in ValueError
            if isinstance(e, ValueError):
                error_str = str(e)
                if "InterruptedError" in error_str and "_pfc_interrupt_check" in error_str:
                    logger.info("Script interrupted (via PFC callback): {}".format(script_path))
                    return {
                        "status": "interrupted",
                        "message": "Script interrupted by user",
                        "result": None,
                        "output": output_text,
                    }

            # Capture complete stack trace for server logging (debugging)
            full_traceback = traceback.format_exc()
            logger.error("Script execution failed with traceback:\n{}".format(full_traceback))

            # Extract only user script frames (filter out server implementation)
            # This prevents exposing backend code to LLM
            tb = sys.exc_info()[2]
            user_frames = []

            # Normalize script_path for comparison (Windows path format consistency)
            normalized_script_path = os.path.normpath(script_path)

            # Walk through traceback to find user script frames
            while tb is not None:
                frame = tb.tb_frame
                filename = frame.f_code.co_filename
                # Normalize filename for comparison (handles G:/ vs G:\ differences)
                normalized_filename = os.path.normpath(filename)
                # Only include frames from user script (not server code)
                if normalized_filename == normalized_script_path or filename == "<string>":
                    user_frames.append(
                        (
                            filename,
                            tb.tb_lineno,
                            frame.f_code.co_name,
                            None,  # No source line (not available for dynamic code)
                        )
                    )
                tb = tb.tb_next

            # Build user-facing error message with filtered traceback
            # Normalize path to LLM-friendly format (forward slashes) using utility
            display_path = path_to_llm_format(script_path)

            if user_frames:
                # Format user script traceback with absolute path in LLM-friendly format
                error_parts = ["Script execution failed:\n"]
                for filename, lineno, name, line in user_frames:
                    # Use absolute path with forward slashes for cross-platform consistency
                    error_parts.append('  File "{}", line {}, in {}\n'.format(display_path, lineno, name))
                error_parts.append("{}: {}".format(type(e).__name__, str(e)))
                error_message = "".join(error_parts)
            else:
                # Fallback if no user frames found (shouldn't happen)
                error_message = "Script execution failed: {}: {}".format(type(e).__name__, str(e))

            return {
                "status": "error",
                "message": error_message,
                "result": None,
                "output": output_text,  # Include output up to error point
            }

        finally:
            # Always restore stdout
            sys.stdout = old_stdout
            # Clear current task and interrupt flag
            clear_current_task()
            clear_interrupt(task_id)

    async def run(self, script_path, description, task_id=None):
        # type: (str, str, Optional[str]) -> Dict[str, Any]
        """
        Submit script to main thread queue and return immediately.

        Args:
            script_path: Absolute path to Python script file
            description: Task description from PFC agent (LLM-provided)
            task_id: Required client-generated task ID (6-char hex)

        Returns:
            Result dictionary:
                - status: "pending" - Task submitted successfully
                - message: str - Submission confirmation message
                - data: Dict with task_id and script_path

        Note:
            - Scripts are executed in IPython main thread via queue
            - Script must define 'result' variable for structured data
            - Print statements are captured and available in output
            - Script has access to 'itasca' module in global scope
        """
        # Validate task_id is provided (backend must generate all task IDs)
        if not task_id:
            return {"status": "error", "message": "task_id is required (must be generated by backend)", "data": None}

        script_name = os.path.basename(script_path)

        try:
            # Read script file
            with open(script_path, "r", encoding="utf-8") as f:
                script_content = f.read()
        except FileNotFoundError:
            return {"status": "error", "message": "Script file not found: {}".format(script_path), "data": None}
        except Exception as e:
            return {"status": "error", "message": "Failed to read script file: {}".format(str(e)), "data": None}

        try:
            # Create output log file for complete output preservation
            # Path: .pfc-mcp/logs/task_{task_id}.log
            log_dir = os.path.join(".pfc-mcp", "logs")
            log_path = os.path.join(log_dir, "task_{}.log".format(task_id))
            output_buffer = FileBuffer(log_path)

            # Submit to main thread queue
            future = self.main_executor.submit(self._execute, script_path, script_content, output_buffer, task_id)

            # Register task with manager
            submit_time = time.time()
            self.task_manager.create_script_task(
                future, script_name, script_path, output_buffer, description, task_id
            )

            # If execution already started before task registration, sync status.
            task = self.task_manager.tasks.get(task_id)
            if task and task.status == "pending":
                try:
                    if future.running():
                        task.status = "running"
                        if task.on_status_change:
                            task.on_status_change(task)
                except Exception:
                    pass

            data = (
                TaskDataBuilder(task_id, "script", script_name, script_path, description)
                .with_timing(submit_time)
                .build()
            )
            return build_response("pending", "Script submitted: {}".format(script_name), data)

        except Exception as e:
            logger.error("Script execution failed: {}".format(e))

            error_message = "Script execution failed: {}".format(str(e))

            data = (
                TaskDataBuilder(task_id, "script", script_name, script_path, description)
                .with_error(error_message)
                .build()
            )
            return build_response("error", error_message, data)

    def _serialize_result(self, result: Any) -> Any:
        """
        Convert PFC objects to JSON-serializable format.

        Args:
            result: Any Python object returned from script execution

        Returns:
            JSON-serializable representation of the result
        """
        if result is None:
            return None
        elif isinstance(result, (str, int, float, bool)):
            return result
        elif isinstance(result, (list, tuple)):
            return [self._serialize_result(item) for item in result]
        elif isinstance(result, dict):
            return {k: self._serialize_result(v) for k, v in result.items()}
        else:
            # For complex PFC objects, return string representation
            return str(result)
