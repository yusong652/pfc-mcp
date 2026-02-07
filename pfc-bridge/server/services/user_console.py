"""
User Console Manager - Manage temporary script files for user Python console.

This module provides script file management for Python commands executed
from the user console (`>` prefix). Each command is saved as a temporary script
file for traceability and uniform task handling.

Script files are stored in: workspace/.user_console/console_XXX.py

Python 3.6 compatible implementation.
"""

import os
import logging
import threading
from typing import Any, Dict, Optional, Tuple

# Module logger
logger = logging.getLogger("PFC-Server")

# Default directory for user console scripts (relative to workspace)
USER_CONSOLE_DIR = ".user_console"

# Counter persistence file (stores the current script counter)
COUNTER_FILE = ".counter"

# Maximum code size in characters (safety limit)
MAX_CODE_SIZE = 10000


class UserConsoleManager:
    """
    Manage temporary script files for user Python console commands.

    Creates sequentially numbered script files (console_001.py, console_002.py, etc.)
    in the workspace/.user_console/ directory. Each file contains exactly one
    user command for traceability.

    Thread-safe: Uses lock for counter management.
    """

    def __init__(self, workspace_path):
        # type: (str) -> None
        """
        Initialize user console manager.

        Args:
            workspace_path: Absolute path to the PFC workspace directory
        """
        self.workspace_path = workspace_path
        self.console_dir = os.path.join(workspace_path, USER_CONSOLE_DIR)
        self._counter = 0
        self._lock = threading.Lock()

        # Ensure directory exists and initialize counter
        self._init_directory()

        logger.info("UserConsoleManager initialized (dir=%s)", self.console_dir)

    def _init_directory(self):
        # type: () -> None
        """Create console directory and initialize counter with three-tier fallback."""
        self._ensure_directory()

        # Three-tier counter initialization:
        # 1. Try loading from persistent counter file
        # 2. Fallback: scan existing script files
        # 3. Final fallback: start from 0

        counter_from_file = self._load_counter()
        if counter_from_file is not None:
            self._counter = counter_from_file
            logger.info("User console counter loaded from file: {}".format(self._counter))
            return

        # Fallback: scan existing scripts
        counter_from_scan = self._scan_existing_scripts()
        self._counter = counter_from_scan
        logger.info("User console counter initialized from scan: {}".format(self._counter))

        # Persist the scanned counter for future use
        if counter_from_scan > 0:
            self._save_counter()

    def _ensure_directory(self):
        # type: () -> bool
        """
        Ensure console directory exists, create if missing.

        Returns:
            bool: True if directory was newly created, False if already existed
        """
        if os.path.exists(self.console_dir):
            # Ensure README exists (for existing directories)
            readme_path = os.path.join(self.console_dir, "README.md")
            if not os.path.exists(readme_path):
                self._create_readme()
            return False

        # Create new directory
        os.makedirs(self.console_dir)
        logger.info("Created user console directory: {}".format(self.console_dir))
        self._create_readme()
        return True

    def _load_counter(self):
        # type: () -> Optional[int]
        """
        Load counter from persistent file.

        Returns:
            int: Counter value if file exists and is valid, None otherwise
        """
        counter_path = os.path.join(self.console_dir, COUNTER_FILE)
        if not os.path.exists(counter_path):
            return None

        try:
            with open(counter_path, 'r', encoding='utf-8') as f:
                value = int(f.read().strip())
                if value >= 0:
                    return value
                logger.warning("Invalid counter value in file: {}".format(value))
                return None
        except (ValueError, IOError) as e:
            logger.warning("Failed to load counter from file: {}".format(e))
            return None

    def _save_counter(self):
        # type: () -> bool
        """
        Persist counter to file (thread-safe, called with lock held).

        Returns:
            bool: True if save successful, False otherwise
        """
        counter_path = os.path.join(self.console_dir, COUNTER_FILE)
        try:
            # Atomic write: write to temp file, then rename
            temp_path = counter_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(str(self._counter))
            os.replace(temp_path, counter_path)
            return True
        except Exception as e:
            logger.warning("Failed to save counter: {}".format(e))
            return False

    def _scan_existing_scripts(self):
        # type: () -> int
        """
        Scan directory to find highest existing script number.

        Returns:
            int: Highest script number found, or 0 if none
        """
        max_counter = 0
        try:
            if not os.path.exists(self.console_dir):
                return 0

            for filename in os.listdir(self.console_dir):
                if filename.startswith("console_") and filename.endswith(".py"):
                    try:
                        # Extract number from console_XXX.py
                        num_str = filename[8:-3]  # Remove "console_" and ".py"
                        num = int(num_str)
                        if num > max_counter:
                            max_counter = num
                    except ValueError:
                        continue
        except Exception as e:
            logger.warning("Failed to scan existing console scripts: {}".format(e))

        return max_counter

    def _create_readme(self):
        # type: () -> None
        """Create README file explaining the user console directory."""
        readme_path = os.path.join(self.console_dir, "README.md")
        readme_content = """# User Console Scripts

This directory contains Python scripts executed by the **user** through the PFC Python console (`>` prefix in CLI).

## Important Notes for LLM

- **Source**: These scripts are created from user console input, NOT by the AI agent
- **Purpose**: Quick exploration, testing, and interactive PFC operations
- **Naming**: `console_XXX.py` where XXX is a sequential number
- **Task Source**: Tasks from these scripts have `source: "user_console"` in task history

## Script Format

Each script contains:
1. Header comment with metadata
2. User's Python code (may include `itasca.command()` calls)

## Viewing History

To see all tasks including user console commands:
- Use `pfc_list_tasks` tool
- Filter by `source: "user_console"` for user-initiated tasks
- Filter by `source: "agent"` for AI-initiated tasks

## Note

Do NOT modify or delete these files manually. They serve as execution history
for traceability and debugging purposes.
"""
        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            logger.info("Created README in user console directory")
        except Exception as e:
            logger.warning("Failed to create README: {}".format(e))

    def _get_next_filename(self):
        # type: () -> Tuple[str, str]
        """
        Get next available filename (thread-safe).

        Increments counter and persists to file for recovery after restart.

        Returns:
            Tuple of (script_name, script_path):
                - script_name: "console_XXX.py"
                - script_path: Full absolute path to the script file
        """
        with self._lock:
            self._counter += 1
            script_name = "console_{:03d}.py".format(self._counter)
            script_path = os.path.join(self.console_dir, script_name)
            # Persist counter after increment
            self._save_counter()
            return script_name, script_path

    def create_script(self, code, description=None):
        # type: (str, Optional[str]) -> Tuple[str, str, str]
        """
        Create a temporary script file for user console code.

        Args:
            code: Python code to execute (single line or multi-line)
            description: Optional description/comment for the script header

        Returns:
            Tuple of (script_name, script_path, code):
                - script_name: "console_XXX.py" (for display)
                - script_path: Full absolute path to the script file
                - code: The code content (for reference)

        Raises:
            ValueError: If code is empty or exceeds size limit
            IOError: If file cannot be written
        """
        # Validate code
        if not code or not code.strip():
            raise ValueError("Code cannot be empty")

        if len(code) > MAX_CODE_SIZE:
            raise ValueError("Code exceeds maximum size limit ({} chars)".format(MAX_CODE_SIZE))

        # Ensure directory exists (handles manual deletion)
        was_recreated = self._ensure_directory()
        if was_recreated:
            logger.info("Console directory was recreated (possibly manually deleted)")

        # Get next filename (also persists counter)
        script_name, script_path = self._get_next_filename()

        # Build script content with header comment
        header_lines = [
            "# User Console Command",
            "# Auto-generated script for user console execution",
        ]
        if description:
            header_lines.append("# Description: {}".format(description))
        header_lines.append("")  # Empty line before code

        script_content = "\n".join(header_lines) + code

        # Write script file
        try:
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            logger.info(
                "Console script created: %s (%d chars)",
                script_name, len(code)
            )

            return script_name, script_path, code

        except Exception as e:
            logger.error("Failed to create console script {}: {}".format(script_name, e))
            raise IOError("Failed to create script file: {}".format(e))

    def get_code_preview(self, code, max_length=50):
        # type: (str, int) -> str
        """
        Generate a truncated preview of code for display.

        Args:
            code: Full code string
            max_length: Maximum preview length

        Returns:
            Truncated code preview (single line)
        """
        # Get first line, strip whitespace
        first_line = code.split('\n')[0].strip()

        if len(first_line) <= max_length:
            return first_line

        return first_line[:max_length - 3] + "..."

    def cleanup_old_scripts(self, keep_count=100):
        # type: (int) -> int
        """
        Remove old script files, keeping the most recent N files.

        Note: Only removes console_*.py files. Counter file (.counter) and
        README.md are preserved.

        Args:
            keep_count: Number of recent scripts to keep

        Returns:
            Number of files removed
        """
        try:
            # List all console scripts with their numbers (excludes .counter and README)
            scripts = []
            for filename in os.listdir(self.console_dir):
                if filename.startswith("console_") and filename.endswith(".py"):
                    try:
                        num_str = filename[8:-3]
                        num = int(num_str)
                        scripts.append((num, filename))
                    except ValueError:
                        continue

            # Sort by number (oldest first)
            scripts.sort(key=lambda x: x[0])

            # Remove oldest scripts if over limit
            removed = 0
            while len(scripts) > keep_count:
                _, filename = scripts.pop(0)
                filepath = os.path.join(self.console_dir, filename)
                try:
                    os.remove(filepath)
                    removed += 1
                except Exception as e:
                    logger.warning("Failed to remove {}: {}".format(filename, e))

            if removed > 0:
                logger.info("Cleaned up {} old console script(s)".format(removed))

            return removed

        except Exception as e:
            logger.error("Failed to cleanup console scripts: {}".format(e))
            return 0

    def reset(self):
        # type: () -> Dict[str, Any]
        """
        Completely reset the user console state.

        Deletes the entire .user_console directory and resets the counter.
        Used for testing/development to get a clean slate.

        Returns:
            Dict with:
                - success: bool
                - message: str
                - deleted_scripts: int
        """
        import shutil

        try:
            deleted_count = 0

            # Count existing scripts before deletion
            if os.path.exists(self.console_dir):
                for filename in os.listdir(self.console_dir):
                    if filename.startswith("console_") and filename.endswith(".py"):
                        deleted_count += 1

                # Delete entire directory
                shutil.rmtree(self.console_dir)
                logger.info("Deleted user console directory: %s", self.console_dir)

            # Reset counter to 0
            with self._lock:
                self._counter = 0

            return {
                "success": True,
                "message": "Reset user console ({} scripts deleted, counter reset to 0)".format(
                    deleted_count
                ),
                "deleted_scripts": deleted_count
            }

        except Exception as e:
            logger.error("Failed to reset user console: {}".format(e))
            return {
                "success": False,
                "message": "Error: {}".format(str(e)),
                "deleted_scripts": 0
            }
