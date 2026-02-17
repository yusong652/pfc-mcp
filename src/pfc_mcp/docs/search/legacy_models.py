"""Unified search result models for PFC documentation systems.

This module provides shared data structures for search results across
command and Python API documentation systems.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DocumentType(Enum):
    """Type of documentation being searched.

    This enum unifies document types across all PFC documentation systems:
    - COMMAND: PFC commands (e.g., "ball create", "contact property")
    - MODEL_PROPERTY: Contact model properties (e.g., "linear", "rrlinear")
    - API: Python SDK APIs (e.g., "itasca.ball.create", "Ball.pos")
    """

    COMMAND = "command"
    MODEL_PROPERTY = "model_property"
    API = "api"


class SearchStrategy(Enum):
    """Search strategy used to find the result.

    Represents which search strategy was used:
    - PATH: Exact path matching (e.g., "itasca.ball.create")
    - KEYWORD: Keyword-based matching (multi-word, partial matching)
    - SEMANTIC: Future embedding-based semantic search
    """

    PATH = "path"
    KEYWORD = "keyword"
    SEMANTIC = "semantic"


@dataclass
class SearchResult:
    """Unified search result across all PFC documentation types.

    This model replaces both CommandSearchResult and the Python API SearchResult,
    providing a single unified interface for all search operations.

    Attributes:
        name: Item name (command name, model name, or API path)
        score: Relevance score (higher = more relevant, typically 0-1000)
        doc_type: Type of documentation (COMMAND, MODEL_PROPERTY, or API)
        category: Category/module name (e.g., "ball", "linear", "contact")
        strategy: Search strategy used (PATH, KEYWORD, or SEMANTIC)
        metadata: Type-specific additional data (optional)

    Examples:
        Command result:
            SearchResult(
                name="ball create",
                score=1000,
                doc_type=DocumentType.COMMAND,
                category="ball",
                strategy=SearchStrategy.KEYWORD,
                metadata={
                    "file": "commands/ball/create.json",
                    "short_description": "Create a single ball",
                    "syntax": "ball create <keyword> ...",
                    "python_available": True
                }
            )

        Model property result:
            SearchResult(
                name="linear",
                score=950,
                doc_type=DocumentType.MODEL_PROPERTY,
                category="linear",
                strategy=SearchStrategy.KEYWORD,
                metadata={
                    "file": "model-properties/linear.json",
                    "full_name": "Linear Model",
                    "description": "Linear elastic-frictional contact model...",
                    "priority": "high"
                }
            )

        Python API result (exact path):
            SearchResult(
                name="itasca.ball.create",
                score=999,
                doc_type=DocumentType.API,
                category="ball",
                strategy=SearchStrategy.PATH,
                metadata=None
            )

        Python API result (Contact type with grouping):
            SearchResult(
                name="itasca.BallBallContact.gap",
                score=1070,
                doc_type=DocumentType.API,
                category="contact",
                strategy=SearchStrategy.KEYWORD,
                metadata={
                    "all_contact_types": ["BallBallContact", "BallFacetContact", ...],
                    "contact_method": "gap"
                }
            )
    """

    name: str
    score: int
    doc_type: DocumentType
    category: str
    strategy: SearchStrategy
    metadata: dict[str, Any] | None = None


# Backward compatibility aliases
# These allow existing code to continue using old names while we migrate
CommandSearchResult = SearchResult  # For command system
# Note: Python API already uses "SearchResult", so no alias needed there
