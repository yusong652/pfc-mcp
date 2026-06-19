"""Type handling for Itasca SDK documentation.

This package provides specialized handling for PFC type systems,
including Contact type aliasing and class-to-module mappings.
"""

from .contact import ALL_CONTACT_TYPES, CONTACT_TYPES, ContactQueryResult, ContactTypeResolver
from .mappings import CLASS_TO_MODULE

__all__ = ["ContactTypeResolver", "CONTACT_TYPES", "ALL_CONTACT_TYPES", "ContactQueryResult", "CLASS_TO_MODULE"]
