"""High-level query interfaces for Itasca documentation search.

This module provides user-facing search APIs that abstract away
the complexity of search engines and adapters.
"""

from itasca_mcp.knowledge.query.api_search import APISearch
from itasca_mcp.knowledge.query.command_search import CommandSearch

__all__ = [
    "CommandSearch",
    "APISearch",
]
