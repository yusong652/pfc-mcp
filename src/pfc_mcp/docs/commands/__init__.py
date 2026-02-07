"""PFC Command Documentation System.

This module provides command documentation loading and formatting capabilities
for PFC commands.

Components:
    - CommandLoader: Load command docs from JSON files
    - CommandFormatter: Format command documentation as markdown

Data Models:
    - CommandSearchResult: Search result with score and metadata
    - DocumentType: Enum for command vs model_property distinction

Note:
    For reference documentation (contact models, range elements), use:
    - pfc_mcp.docs.references

    For command search functionality, use the unified search system:
    - pfc_mcp.docs.query.CommandSearch (BM25-based search)
"""

from pfc_mcp.docs.commands.loader import CommandLoader
from pfc_mcp.docs.commands.formatter import CommandFormatter
from pfc_mcp.docs.commands.models import (
    CommandSearchResult,
    DocumentType
)

__all__ = [
    # Core components
    "CommandLoader",
    "CommandFormatter",
    # Data models
    "CommandSearchResult",
    "DocumentType"
]
