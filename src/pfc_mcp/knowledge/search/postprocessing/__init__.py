"""Search result post-processing utilities.

This module provides utilities for post-processing search results,
including Contact API consolidation, component API consolidation,
result filtering, and metadata enrichment.
"""

from pfc_mcp.knowledge.search.postprocessing.component_consolidation import consolidate_component_apis
from pfc_mcp.knowledge.search.postprocessing.contact_consolidation import consolidate_contact_apis

__all__ = ["consolidate_contact_apis", "consolidate_component_apis"]
