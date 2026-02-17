"""PFC Reference Documentation System.

This module provides reference documentation loading and formatting capabilities
for PFC reference items (contact models, range elements).

Components:
    - ReferenceLoader: Load reference docs from JSON files
    - ReferenceFormatter: Format reference documentation as markdown
"""

from pfc_mcp.docs.references.formatter import ReferenceFormatter
from pfc_mcp.docs.references.loader import ReferenceLoader

__all__ = [
    "ReferenceLoader",
    "ReferenceFormatter",
]
