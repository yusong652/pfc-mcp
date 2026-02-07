"""Data models for PFC SDK documentation system.

This module defines the core data structures used throughout the SDK
documentation system, providing type-safe contracts for search results
and API documentation.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class SearchStrategy(Enum):
    """Search strategy types.

    Represents which search strategy was used to find an API:
    - PATH: Exact path matching (e.g., "itasca.ball.create")
    - KEYWORD: Natural language keyword search
    - SEMANTIC: Future embedding-based semantic search
    """
    PATH = "path"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"


@dataclass
class SearchResult:
    """Unified search result structure.

    Attributes:
        api_name: Internal API name (e.g., "Contact.gap" for contact methods)
        score: Match score (999 for exact path match, 1-N for keyword overlap)
        strategy: Which search strategy found this result
        metadata: Optional context (Contact type info, query details, etc.)

    Examples:
        >>> SearchResult("itasca.ball.create", 999, SearchStrategy.PATH, None)
        >>> SearchResult("Contact.gap", 999, SearchStrategy.PATH,
        ...              {"contact_type": "BallBallContact"})
    """
    api_name: str
    score: int
    strategy: SearchStrategy
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class APIDocumentation:
    """Structured API documentation.

    This model represents the complete documentation for a PFC Python SDK API,
    parsed from JSON documentation files.

    Attributes:
        api_name: Full API name (e.g., "itasca.ball.create")
        signature: Function/method signature
        description: Detailed description (markdown format)
        parameters: List of parameter definitions
        returns: Return value information (type and description)
        examples: Usage examples with code snippets
        limitations: Known limitations (optional)
        fallback_commands: Alternative PFC commands to use instead (optional)
        best_practices: Recommended usage patterns (optional)
        notes: Additional notes (optional)
        see_also: Related APIs (optional)
    """
    api_name: str
    signature: str
    description: str
    parameters: List[Dict[str, Any]]
    returns: Optional[Dict[str, str]] = None
    examples: Optional[List[Dict[str, str]]] = None
    limitations: Optional[str] = None
    fallback_commands: Optional[List[str]] = None
    best_practices: Optional[List[str]] = None
    notes: Optional[List[str]] = None
    see_also: Optional[List[str]] = None
