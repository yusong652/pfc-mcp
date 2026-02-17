"""Search infrastructure for PFC documentation systems.

Provides unified search components used by both command search
and Python API search systems.
"""

from pfc_mcp.knowledge.search.base import SearchStrategy
from pfc_mcp.knowledge.search.legacy_models import (
    CommandSearchResult,  # Backward compatibility alias
    DocumentType,
    SearchResult,
)
from pfc_mcp.knowledge.search.legacy_models import SearchStrategy as SearchStrategyEnum

__all__ = [
    "SearchStrategy",
    "SearchResult",
    "DocumentType",
    "SearchStrategyEnum",
    "CommandSearchResult",
]
