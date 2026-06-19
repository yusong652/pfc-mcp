"""Shared models for Itasca documentation search system.

This package provides unified data models for the search infrastructure,
enabling consistent handling of different document types (commands, APIs, etc.).
"""

from itasca_mcp.knowledge.models.document import DocumentType, SearchDocument
from itasca_mcp.knowledge.models.search_result import SearchResult

__all__ = ["DocumentType", "SearchDocument", "SearchResult"]
