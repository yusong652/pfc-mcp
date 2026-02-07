"""Search infrastructure for PFC documentation systems.

Provides unified search components used by both command search
and Python API search systems.
"""

from pfc_mcp.docs.search.base import SearchStrategy
from pfc_mcp.docs.search.legacy_models import (
    SearchResult,
    DocumentType,
    SearchStrategy as SearchStrategyEnum,
    CommandSearchResult  # Backward compatibility alias
)

__all__ = [
    "SearchStrategy",
    "SearchResult",
    "DocumentType",
    "SearchStrategyEnum",
    "CommandSearchResult",
]
