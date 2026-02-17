"""High-level command search interface.

This module provides a simple, user-friendly API for searching PFC commands.
Model properties are handled separately via pfc_browse_reference tool.
"""

from typing import Any

from pfc_mcp.docs.adapters.command_adapter import CommandDocumentAdapter
from pfc_mcp.docs.models.search_result import SearchResult
from pfc_mcp.docs.search.engines.bm25_engine import BM25SearchEngine


class CommandSearch:
    """Command search interface for PFC documentation.

    This class provides a high-level API for searching PFC commands
    using BM25 algorithm with multi-field scoring.

    Features:
    - Automatic index initialization (lazy loading)
    - Singleton pattern for efficient memory usage
    - Support for filtering by category
    - BM25 with multi-field scoring (name=0.5, keywords=0.3, description=0.2)

    Note: For contact model properties, use pfc_browse_reference tool directly.

    Usage:
        >>> # Basic search
        >>> results = CommandSearch.search("ball create", top_k=5)
        >>> results[0].document.title
        "ball create"

        >>> # With category filter
        >>> results = CommandSearch.search("create", category="ball")
        >>> results[0].document.category
        "ball"
    """

    # Singleton instance
    _engine: BM25SearchEngine | None = None

    @classmethod
    def _get_engine(cls) -> BM25SearchEngine:
        """Get or create BM25 search engine (singleton pattern).

        Returns:
            BM25SearchEngine instance (shared across all calls)
        """
        if cls._engine is None:
            cls._engine = BM25SearchEngine(document_loader=CommandDocumentAdapter.load_commands)
            cls._engine.build()

        return cls._engine

    @classmethod
    def search(
        cls, query: str, top_k: int = 10, category: str | None = None, min_score: float | None = None
    ) -> list[SearchResult]:
        """Search for PFC commands.

        Args:
            query: Search query string
                  Examples: "ball create", "contact property", "model solve"
            top_k: Maximum number of results to return (default: 10)
            category: Optional category filter
                     Examples: "ball", "contact", "model"
            min_score: Optional minimum score threshold

        Returns:
            List of SearchResult objects sorted by score (highest first)
            Empty list if no matches found

        Example:
            >>> results = CommandSearch.search("ball create")
            >>> results[0].document.title
            "ball create"

            >>> results = CommandSearch.search("create", category="ball")
            >>> results[0].document.category
            "ball"
        """
        engine = cls._get_engine()

        # Build filter dictionary
        filters: dict[str, Any] = {}

        if category is not None:
            filters["category"] = category

        if min_score is not None:
            filters["min_score"] = min_score

        # Execute search
        results = engine.search(query=query, top_k=top_k, filters=filters if filters else None)

        return results

    @classmethod
    def search_commands_only(cls, query: str, top_k: int = 10, category: str | None = None) -> list[SearchResult]:
        """Search for commands (alias for search method).

        Kept for backward compatibility.

        Args:
            query: Search query string
            top_k: Maximum number of results to return (default: 10)
            category: Optional category filter

        Returns:
            List of SearchResult objects
        """
        return cls.search(query=query, top_k=top_k, category=category)

    @classmethod
    def get_by_category(cls, category: str, top_k: int = 20) -> list[SearchResult]:
        """Get all commands in a specific category.

        Args:
            category: Category name (e.g., "ball", "contact", "model")
            top_k: Maximum number of results (default: 20)

        Returns:
            List of SearchResult objects in the category

        Example:
            >>> results = CommandSearch.get_by_category("ball")
            >>> all(r.document.category == "ball" for r in results)
            True
        """
        return cls.search(query=category, top_k=top_k, category=category)

    @classmethod
    def rebuild_index(cls) -> None:
        """Rebuild search index from scratch.

        Use this when:
        - Documentation files have been updated
        - Index parameters need to be changed
        - Troubleshooting index issues
        """
        if cls._engine is not None:
            cls._engine.rebuild()

    @classmethod
    def get_index_stats(cls) -> dict[str, Any]:
        """Get search index statistics.

        Returns:
            Dictionary with index statistics:
            - doc_count: Number of indexed documents
            - name_field: Name field statistics
            - description_field: Description field statistics
            - keywords_field: Keywords field statistics
        """
        engine = cls._get_engine()
        return engine.get_index_stats()
