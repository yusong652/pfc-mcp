"""High-level query interfaces for PFC documentation search.

This module provides user-facing search APIs that abstract away
the complexity of search engines and adapters.
"""

from pfc_mcp.docs.query.command_search import CommandSearch
from pfc_mcp.docs.query.api_search import APISearch

__all__ = [
    'CommandSearch',
    'APISearch',
]
