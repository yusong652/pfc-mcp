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
    - pfc_mcp.knowledge.references

    For command search functionality, use the unified search system:
    - pfc_mcp.knowledge.query.CommandSearch (BM25-based search)
"""

from pfc_mcp.knowledge.commands.formatter import CommandFormatter
from pfc_mcp.knowledge.commands.loader import CommandLoader
from pfc_mcp.knowledge.commands.models import CommandSearchResult, DocumentType

__all__ = [
    # Core components
    "CommandLoader",
    "CommandFormatter",
    # Data models
    "CommandSearchResult",
    "DocumentType",
]
