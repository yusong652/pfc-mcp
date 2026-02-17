"""Search engine implementations for PFC documentation search.

This module provides high-level search engines that orchestrate
indexing, scoring, and result formatting.
"""

from pfc_mcp.knowledge.search.engines.base_engine import BaseSearchEngine
from pfc_mcp.knowledge.search.engines.bm25_engine import BM25SearchEngine

__all__ = [
    "BaseSearchEngine",
    "BM25SearchEngine",
]
