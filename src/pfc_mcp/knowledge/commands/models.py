"""Data models for PFC command documentation system.

DEPRECATED: This module is kept for backward compatibility only.
New code should use pfc_mcp.knowledge.search.legacy_models instead.
"""

# Import from unified models for backward compatibility
from pfc_mcp.knowledge.search.legacy_models import DocumentType, SearchStrategy
from pfc_mcp.knowledge.search.legacy_models import SearchResult as CommandSearchResult

# Re-export for backward compatibility
__all__ = ["CommandSearchResult", "DocumentType", "SearchStrategy"]
