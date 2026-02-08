"""Validation models and utilities for PFC MCP tools."""

from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Optional

from pydantic import Field
from pydantic.functional_validators import AfterValidator


# Search limits
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 20

# Task/output pagination
DEFAULT_OUTPUT_LINES = 64
MAX_OUTPUT_LINES = 200
DEFAULT_TASK_LIST_LIMIT = 32
MAX_TASK_LIST_LIMIT = 100

# Timeout constraints (seconds)
MIN_TIMEOUT_S = 1
MAX_TIMEOUT_S = 600

# Wait constraints (seconds)
MIN_WAIT_SECONDS = 1
MAX_WAIT_SECONDS = 3600

# Description constraints
DESCRIPTION_MAX_LENGTH = 200


def normalize_input(value: Optional[str], lowercase: bool = False) -> str:
    """Normalize user input: collapse whitespace, optionally lowercase."""
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


def validate_script_path(value: str) -> str:
    """Validate entry script path."""
    stripped = validate_non_empty_string(value)
    if not (PurePosixPath(stripped).is_absolute() or PureWindowsPath(stripped).is_absolute()):
        raise ValueError("entry_script must be an absolute path")
    return stripped


def validate_task_description(value: str) -> str:
    """Validate task description text."""
    stripped = validate_non_empty_string(value)
    if len(stripped) > DESCRIPTION_MAX_LENGTH:
        raise ValueError(f"description is too long (max {DESCRIPTION_MAX_LENGTH} chars)")
    return stripped


def validate_output_path(value: str) -> str:
    """Validate screenshot output path."""
    stripped = validate_non_empty_string(value)
    if not (PurePosixPath(stripped).is_absolute() or PureWindowsPath(stripped).is_absolute()):
        raise ValueError("output_path must be an absolute path")
    if not stripped.lower().endswith(".png"):
        raise ValueError("output_path must end with .png")
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
        ),
    ),
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
        ),
    ),
]

# Search limit
SearchLimit = Annotated[
    int,
    Field(
        default=DEFAULT_SEARCH_LIMIT,
        ge=1,
        le=MAX_SEARCH_LIMIT,
        description=f"Maximum number of results (1-{MAX_SEARCH_LIMIT}).",
    ),
]

TaskId = Annotated[
    str,
    AfterValidator(validate_non_empty_string),
    Field(..., description="Task ID returned by pfc_execute_task or pfc_execute_code"),
]

ScriptPath = Annotated[
    str,
    AfterValidator(validate_script_path),
    Field(..., description="Absolute path to entry Python script in PFC workspace"),
]

TaskDescription = Annotated[
    str,
    AfterValidator(validate_task_description),
    Field(..., min_length=1, max_length=DESCRIPTION_MAX_LENGTH, description="Brief task purpose"),
]

TimeoutSeconds = Annotated[
    Optional[int],
    Field(
        default=None,
        ge=MIN_TIMEOUT_S,
        le=MAX_TIMEOUT_S,
        description="Execution timeout in seconds. Null means no timeout.",
    ),
]

RunInBackground = Annotated[
    bool,
    Field(default=True, description="Return immediately with task ID when true"),
]

SkipNewestTasks = Annotated[
    int,
    Field(default=0, ge=0, description="Skip N most recent tasks before listing"),
]

TaskListLimit = Annotated[
    int,
    Field(default=DEFAULT_TASK_LIST_LIMIT, ge=1, le=MAX_TASK_LIST_LIMIT, description="Max tasks to return"),
]

SkipNewestLines = Annotated[
    int,
    Field(default=0, ge=0, description="Skip N newest output lines before pagination"),
]

OutputLimit = Annotated[
    int,
    Field(default=DEFAULT_OUTPUT_LINES, ge=1, le=MAX_OUTPUT_LINES, description="Output lines per page"),
]

FilterText = Annotated[
    Optional[str],
    Field(default=None, description="Only keep output lines containing this text"),
]

WaitSeconds = Annotated[
    float,
    Field(
        default=MIN_WAIT_SECONDS,
        ge=MIN_WAIT_SECONDS,
        le=MAX_WAIT_SECONDS,
        description="Wait time before querying status",
    ),
]

ConsoleCode = Annotated[
    str,
    AfterValidator(validate_non_empty_string),
    Field(..., min_length=1, description="Python code to execute in PFC user console"),
]

ConsoleTimeoutSeconds = Annotated[
    int,
    Field(default=30, ge=MIN_TIMEOUT_S, le=MAX_TIMEOUT_S, description="Console execution timeout in seconds"),
]

PlotOutputPath = Annotated[
    str,
    AfterValidator(validate_output_path),
    Field(..., description="Absolute output path for plot screenshot PNG"),
]
