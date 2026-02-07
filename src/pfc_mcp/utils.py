"""Validation models and utilities for PFC MCP tools.

Provides Annotated types with Pydantic validation for tool parameters.
"""

from typing import Annotated, Optional

from pydantic import Field
from pydantic.functional_validators import AfterValidator


# Search limits
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 20


def normalize_input(value: Optional[str], lowercase: bool = False) -> str:
    """Normalize user input: collapse whitespace, optionally lowercase.

    Args:
        value: Input string to normalize
        lowercase: Whether to convert to lowercase

    Returns:
        Normalized string with collapsed whitespace
    """
    if value is None:
        return ""
    normalized = " ".join(value.split())
    return normalized.lower() if lowercase else normalized


def validate_non_empty_string(value: str) -> str:
    """Validate that a string is not empty after stripping whitespace."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("Value cannot be empty or whitespace only")
    return stripped


# Search query for commands
SearchQuery = Annotated[
    str,
    AfterValidator(validate_non_empty_string),
    Field(
        ...,
        min_length=1,
        description=(
            "Search keywords for PFC commands. Examples: 'ball create', "
            "'contact property', 'model solve'. Case-insensitive."
        )
    )
]

# Python API search query
PythonAPISearchQuery = Annotated[
    str,
    AfterValidator(validate_non_empty_string),
    Field(
        ...,
        min_length=1,
        description=(
            "Search keywords for PFC Python SDK API. Examples: 'ball pos', "
            "'contact force', 'model solve'. Case-insensitive."
        )
    )
]

# Search limit
SearchLimit = Annotated[
    int,
    Field(
        default=DEFAULT_SEARCH_LIMIT,
        ge=1,
        le=MAX_SEARCH_LIMIT,
        description=f"Maximum number of results (1-{MAX_SEARCH_LIMIT})."
    )
]
