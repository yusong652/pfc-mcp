"""
Path normalization utilities for PFC server.

Provides LLM-friendly path formatting (forward slashes) for cross-platform consistency.
This is a lightweight version adapted from backend/infrastructure/mcp/utils/path_normalization.py
"""


def path_to_llm_format(path):
    # type: (str) -> str
    """
    Convert a path to LLM-friendly format (forward slashes).

    This ensures all paths shown to the LLM use consistent forward slash format,
    regardless of the underlying platform.

    Args:
        path: Path string to format

    Returns:
        Path string with forward slashes

    Example:
        >>> path_to_llm_format("C:\\Users\\test\\file.txt")
        'C:/Users/test/file.txt'
    """
    # Normalize to forward slashes for LLM consistency
    return path.replace('\\', '/')
