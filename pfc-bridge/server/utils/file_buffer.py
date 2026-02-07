"""
File Buffer - Disk-based output capture for task execution.

Provides a file-like buffer that writes directly to disk, ensuring
complete output preservation for long-running simulations.

Uses Python's built-in file buffering (8KB default) to minimize
disk I/O while maintaining data safety.

Python 3.6 compatible implementation.
"""

import os
import logging
from typing import Optional

# Module logger
logger = logging.getLogger("PFC-Server")

# Default tail size for real-time monitoring (100KB)
DEFAULT_TAIL_SIZE = 100_000


class FileBuffer:
    """
    A file-like buffer that writes output directly to disk.

    Designed for capturing stdout from long-running PFC simulations.
    Uses Python's file buffering to batch writes efficiently.

    Features:
    - Complete output preservation (no truncation)
    - Efficient batched writes via Python buffering
    - Tail reading for real-time monitoring
    - Thread-safe for single writer

    Example:
        buffer = FileBuffer("/path/to/task_abc123.log")
        sys.stdout = buffer

        # ... script executes with many print() calls ...

        output = buffer.getvalue()  # Full output
        recent = buffer.get_tail(50000)  # Last 50KB
        buffer.close()
    """

    def __init__(self, log_path, buffer_size=8192):
        # type: (str, int) -> None
        """
        Initialize file buffer.

        Args:
            log_path: Path to output log file
            buffer_size: Python file buffer size in bytes (default: 8KB)
        """
        self._path = log_path
        self._size = 0
        self._closed = False

        # Ensure directory exists
        log_dir = os.path.dirname(log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Open file with buffering for efficient writes
        self._file = open(log_path, 'w', encoding='utf-8', buffering=buffer_size)

        logger.debug("FileBuffer created: {}".format(log_path))

    def write(self, s):
        # type: (str) -> int
        """
        Write string to file.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        if self._closed or not s:
            return 0

        self._file.write(s)
        self._size += len(s)
        return len(s)

    def getvalue(self, max_size=None):
        # type: (Optional[int]) -> str
        """
        Read output from file.

        Args:
            max_size: Optional maximum bytes to read from end.
                      If None, reads entire file.

        Returns:
            Output content (possibly truncated with notice)
        """
        self._ensure_flushed()

        if not os.path.exists(self._path):
            return ""

        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                if max_size is None or self._size <= max_size:
                    return f.read()

                # Read only tail
                return self._read_tail(f, max_size)

        except Exception as e:
            logger.warning("Failed to read output file: {}".format(e))
            return ""

    def get_tail(self, tail_bytes=DEFAULT_TAIL_SIZE):
        # type: (int) -> str
        """
        Read last N bytes of output (for real-time monitoring).

        Args:
            tail_bytes: Number of bytes to read from end

        Returns:
            Recent output content
        """
        return self.getvalue(max_size=tail_bytes)

    def _read_tail(self, f, max_size):
        # type: (any, int) -> str #type: ignore
        """Read tail of file with truncation notice."""
        # Seek to near end
        seek_pos = max(0, self._size - max_size)
        f.seek(seek_pos)

        # Skip partial line
        if seek_pos > 0:
            f.readline()

        content = f.read()
        truncated = self._size - len(content) - (seek_pos if seek_pos == 0 else 0)

        if truncated > 0:
            header = "[... {} earlier bytes, showing recent output ...]\n\n".format(
                self._format_bytes(truncated)
            )
            return header + content

        return content

    def get_size(self):
        # type: () -> int
        """Get current output size in bytes."""
        return self._size

    def get_path(self):
        # type: () -> str
        """Get log file path."""
        return self._path

    def flush(self):
        # type: () -> None
        """Flush buffered content to disk."""
        if not self._closed:
            self._file.flush()

    def close(self):
        # type: () -> None
        """Close the file buffer."""
        if not self._closed:
            self._file.close()
            self._closed = True
            logger.debug("FileBuffer closed: {} ({})".format(
                self._path, self._format_bytes(self._size)
            ))

    def _ensure_flushed(self):
        # type: () -> None
        """Ensure all buffered content is written to disk."""
        if not self._closed and self._file:
            try:
                self._file.flush()
            except (ValueError, OSError):
                # File already closed or I/O error
                pass

    @staticmethod
    def _format_bytes(num_bytes):
        # type: (int) -> str
        """Format bytes in human-readable form."""
        if num_bytes < 1024:
            return "{} bytes".format(num_bytes)
        elif num_bytes < 1024 * 1024:
            return "{:.1f} KB".format(num_bytes / 1024)
        else:
            return "{:.1f} MB".format(num_bytes / (1024 * 1024))

    # File-like interface for sys.stdout compatibility
    def readable(self):
        # type: () -> bool
        return False

    def writable(self):
        # type: () -> bool
        return not self._closed

    def seekable(self):
        # type: () -> bool
        return False

    def isatty(self):
        # type: () -> bool
        """Check if buffer is connected to a terminal (always False for file buffer)."""
        return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
