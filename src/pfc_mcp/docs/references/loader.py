"""Data loading layer for PFC reference documentation.

This module loads reference documentation (contact models, range elements)
from JSON files with caching for performance.

Responsibilities:
- Load references index (2 categories: contact-models, range-elements)
- Load individual reference item documentation
- Cache loaded data to avoid repeated I/O
"""

import json
from functools import lru_cache
from typing import Any

from pfc_mcp.docs.config import PFC_REFERENCES_ROOT


class ReferenceLoader:
    """Loads and caches PFC reference documentation.

    This class provides static methods for loading reference docs
    (contact models, range elements). All methods use caching
    to avoid repeated file I/O.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def load_index() -> dict[str, Any]:
        """Load the main references index file.

        Returns:
            References index with:
                - categories: Available reference categories
                - navigation: Navigation hints
                - notes: Usage notes

        Example:
            >>> index = ReferenceLoader.load_index()
            >>> categories = index["categories"]
            >>> "contact-models" in categories
            True
        """
        index_path = PFC_REFERENCES_ROOT / "index.json"
        if not index_path.exists():
            return {}

        with open(index_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_category_index(category: str) -> dict[str, Any] | None:
        """Load index for a specific reference category.

        Args:
            category: Category name (e.g., "contact-models", "range-elements")

        Returns:
            Category index dict or None if not found

        Example:
            >>> index = ReferenceLoader.load_category_index("contact-models")
            >>> len(index["models"])
            5
            >>> index = ReferenceLoader.load_category_index("range-elements")
            >>> len(index["elements"])
            24
        """
        refs_index = ReferenceLoader.load_index()
        categories = refs_index.get("categories", {})

        if category not in categories:
            return None

        cat_data = categories[category]
        index_file = cat_data.get("index_file")
        if not index_file:
            return None

        index_path = PFC_REFERENCES_ROOT / index_file
        if not index_path.exists():
            return None

        with open(index_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_item_doc(category: str, item_name: str) -> dict[str, Any] | None:
        """Load documentation for a specific reference item.

        Args:
            category: Category name (e.g., "contact-models", "range-elements")
            item_name: Item name (e.g., "linear", "cylinder", "group")

        Returns:
            Item documentation dict or None if not found

        Example:
            >>> doc = ReferenceLoader.load_item_doc("contact-models", "linear")
            >>> doc["full_name"]
            "Linear Model"
            >>> doc = ReferenceLoader.load_item_doc("range-elements", "cylinder")
            >>> doc["name"]
            "cylinder"
        """
        refs_index = ReferenceLoader.load_index()
        categories = refs_index.get("categories", {})

        if category not in categories:
            return None

        cat_data = categories[category]
        directory = cat_data.get("directory", category)

        # Try loading the item file directly
        doc_path = PFC_REFERENCES_ROOT / directory / f"{item_name}.json"
        if not doc_path.exists():
            return None

        with open(doc_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_item_list(category: str) -> list[dict[str, Any]]:
        """Get list of items in a reference category.

        Args:
            category: Category name (e.g., "contact-models", "range-elements")

        Returns:
            List of item metadata dicts

        Example:
            >>> items = ReferenceLoader.get_item_list("contact-models")
            >>> len(items)
            5
            >>> items = ReferenceLoader.get_item_list("range-elements")
            >>> len(items)
            24
        """
        index = ReferenceLoader.load_category_index(category)
        if not index:
            return []

        # contact-models uses "models" key, range-elements uses "elements" key
        if "models" in index:
            return index["models"]
        elif "elements" in index:
            return index["elements"]
        else:
            return []

    @staticmethod
    def clear_cache():
        """Clear all cached data.

        Useful for testing or when documentation files are updated.
        """
        ReferenceLoader.load_index.cache_clear()
