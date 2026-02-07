"""
Shared helper functions for message handlers.
"""

from typing import Any, Dict, Optional, Tuple


def require_field(data, field_name, request_id, response_type="result"):
    # type: (Dict[str, Any], str, str, str) -> Tuple[Any, Optional[Dict[str, Any]]]
    """
    Validate that a required field exists and is non-empty.

    Args:
        data: Request data dictionary
        field_name: Name of the required field
        request_id: Request ID for error response
        response_type: Response type for error (default: "result")

    Returns:
        Tuple of (value, error_response):
            - (value, None) if field exists and is non-empty
            - (None, error_dict) if field is missing or empty
    """
    value = data.get(field_name, "")
    if not value:
        return None, {
            "type": response_type,
            "request_id": request_id,
            "status": "error",
            "message": "{} required".format(field_name),
            "data": None
        }
    return value, None


def truncate_message(message, max_length=5000):
    # type: (str, int) -> str
    """
    Truncate message if too long to prevent WebSocket/JSON size issues.

    Args:
        message: Original message string
        max_length: Maximum message length (default: 5000 characters)

    Returns:
        Truncated message with indicator if truncation occurred
    """
    if len(message) <= max_length:
        return message
    return message[:max_length] + f"\n... (truncated from {len(message)} chars)"
