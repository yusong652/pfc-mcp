"""Base search strategy interface.

This module defines the abstract base class for all search strategies,
ensuring a consistent interface across different search implementations.
"""

from abc import ABC, abstractmethod

from pfc_mcp.docs.search.legacy_models import SearchResult


class SearchStrategy(ABC):
    """Abstract base class for search strategies.

    All search strategies must implement the search() and can_handle() methods.
    This allows the searcher orchestrator to dynamically select and compose
    strategies based on the query characteristics.
    """

    @abstractmethod
    def search(self, query: str, top_n: int = 3) -> list[SearchResult]:
        """Execute search with this strategy.

        Args:
            query: Search query string (path or natural language)
            top_n: Maximum number of results to return

        Returns:
            List of SearchResult objects sorted by score (highest first)

        Example:
            >>> # Note: Direct strategy use is deprecated
            >>> # Use APISearch.search() instead for unified BM25 search
            >>> from pfc_mcp.docs.query import APISearch
            >>> results = APISearch.search("itasca.ball.create")
            >>> results[0].document.name
            "itasca.ball.create"
        """
        pass

    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Check if this strategy can handle the query.

        Args:
            query: Search query string

        Returns:
            True if this strategy is applicable to the query

        Example:
            >>> # Note: Direct strategy use is deprecated
            >>> # BM25 search handles all query types automatically
            >>> from pfc_mcp.docs.query import APISearch
            >>> APISearch.search("itasca.ball.create")  # Path query
            >>> APISearch.search("create a ball")  # Natural language query
        """
        pass
