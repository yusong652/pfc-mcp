"""Base search engine interface for PFC documentation search.

This module defines the abstract interface that all search engines must implement,
ensuring consistent behavior across different search algorithms.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pfc_mcp.docs.models.document import SearchDocument
from pfc_mcp.docs.models.search_result import SearchResult


class BaseSearchEngine(ABC):
    """Abstract base class for search engines.

    All search engines must implement this interface to ensure consistent
    behavior across different search algorithms (BM25, hybrid, semantic, etc.).

    The engine is responsible for:
    - Building and maintaining search indices
    - Executing queries with filtering and ranking
    - Returning standardized SearchResult objects

    Design Philosophy:
    - Single Responsibility: Each engine handles one search algorithm
    - Dependency Injection: Document loader passed in constructor
    - Immutable Results: Returns new SearchResult objects
    - Pluggable: Easy to swap engines without changing client code

    Usage:
        >>> engine = BM25SearchEngine(document_loader=load_docs)
        >>> results = engine.search("ball porosity", top_k=5)
        >>> for result in results:
        ...     print(f"{result.document.title}: {result.score}")
    """

    def __init__(self, document_loader: Callable[[], list[SearchDocument]]):
        """Initialize search engine with document loader.

        Args:
            document_loader: Callable that returns list of SearchDocument objects.
                           This allows lazy loading and caching strategies.

        Example:
            >>> from pfc_mcp.docs.adapters.command_adapter import CommandDocumentAdapter
            >>> engine = BM25SearchEngine(document_loader=CommandDocumentAdapter.load_all)
        """
        self.document_loader = document_loader
        self.documents: list[SearchDocument] = []
        self._is_built = False

    @abstractmethod
    def build(self) -> None:
        """Build search index from loaded documents.

        This method should:
        1. Load documents using self.document_loader()
        2. Build internal search indices
        3. Set self._is_built = True

        Raises:
            Exception: If index building fails

        Example:
            >>> engine = BM25SearchEngine(document_loader=load_docs)
            >>> engine.build()
            >>> engine._is_built
            True
        """
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 10, filters: dict[str, Any] | None = None) -> list[SearchResult]:
        """Execute search query with optional filtering.

        Args:
            query: Search query string (e.g., "ball porosity", "create contact")
            top_k: Maximum number of results to return (default: 10)
            filters: Optional filters to apply:
                    - doc_type: Filter by DocumentType (e.g., "command", "python_api")
                    - category: Filter by category (e.g., "ball", "contact")
                    - min_score: Minimum score threshold

        Returns:
            List of SearchResult objects sorted by score (highest first).
            Empty list if no matches found or query is invalid.

        Raises:
            ValueError: If engine not built (call build() first)

        Example:
            >>> results = engine.search("ball create", top_k=5)
            >>> results[0].document.title
            "ball create"

            >>> results = engine.search(
            ...     "contact",
            ...     top_k=10,
            ...     filters={"doc_type": "command", "category": "contact"}
            ... )
        """
        pass

    def rebuild(self) -> None:
        """Rebuild search index from scratch.

        Useful when:
        - Documents have been updated
        - Index parameters have changed
        - Cache needs to be cleared

        Example:
            >>> engine.rebuild()
        """
        self._is_built = False
        self.build()

    def is_built(self) -> bool:
        """Check if search engine is ready for queries.

        Returns:
            True if build() has been called successfully

        Example:
            >>> engine.is_built()
            False
            >>> engine.build()
            >>> engine.is_built()
            True
        """
        return self._is_built

    def get_document_count(self) -> int:
        """Get total number of indexed documents.

        Returns:
            Number of documents in the index

        Example:
            >>> engine.build()
            >>> engine.get_document_count()
            120  # 115 commands + 5 model properties
        """
        return len(self.documents)

    def _apply_filters(self, results: list[SearchResult], filters: dict[str, Any] | None) -> list[SearchResult]:
        """Apply filters to search results.

        This is a helper method that can be used by concrete implementations.

        Args:
            results: List of SearchResult objects to filter
            filters: Filter criteria (doc_type, category, min_score)

        Returns:
            Filtered list of SearchResult objects

        Example:
            >>> filtered = self._apply_filters(
            ...     results,
            ...     filters={"doc_type": "command", "min_score": 5.0}
            ... )
        """
        if not filters:
            return results

        filtered = results

        # Filter by document type
        if "doc_type" in filters:
            doc_type_filter = filters["doc_type"]
            filtered = [r for r in filtered if r.document.doc_type.value == doc_type_filter]

        # Filter by category
        # Supports both exact match and partial match
        # Examples: "ball" matches "itasca.ball", "contact" matches "itasca.contact"
        if "category" in filters:
            category_filter = filters["category"].lower()
            filtered = [
                r
                for r in filtered
                if r.document.category
                and (
                    r.document.category.lower() == category_filter
                    or r.document.category.lower().endswith(f".{category_filter}")
                )
            ]

        # Filter by minimum score
        if "min_score" in filters:
            min_score = filters["min_score"]
            filtered = [r for r in filtered if r.score >= min_score]

        return filtered
