"""Document adapters for PFC search system.

This package provides adapters to convert raw documentation data from loaders
into unified SearchDocument models. Each adapter handles a specific document
source (commands, Python API, etc.).
"""

from pfc_mcp.docs.adapters.api_adapter import APIDocumentAdapter
from pfc_mcp.docs.adapters.command_adapter import CommandDocumentAdapter

__all__ = ["CommandDocumentAdapter", "APIDocumentAdapter"]
