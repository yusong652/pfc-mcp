"""Document adapters for Itasca documentation search system.

This package provides adapters to convert raw documentation data from loaders
into unified SearchDocument models. Each adapter handles a specific document
source (commands, Python API, etc.).
"""

from itasca_mcp.knowledge.adapters.api_adapter import APIDocumentAdapter
from itasca_mcp.knowledge.adapters.command_adapter import CommandDocumentAdapter

__all__ = ["CommandDocumentAdapter", "APIDocumentAdapter"]
