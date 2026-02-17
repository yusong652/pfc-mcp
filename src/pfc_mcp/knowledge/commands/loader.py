"""Data loading layer for PFC command documentation.

This module loads command documentation from JSON files with caching
for performance.

Responsibilities:
- Load index.json (command catalog with 115 commands across 7 categories)
- Load individual command documentation files
- Cache loaded data to avoid repeated I/O
"""

import json
from functools import lru_cache
from typing import Any, cast

from pfc_mcp.knowledge.config import PFC_COMMAND_DOCS_ROOT


class CommandLoader:
    """Loads and caches PFC command documentation.

    This class provides static methods for loading command docs.
    All methods use caching to avoid repeated file I/O.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def load_index() -> dict[str, Any]:
        """Load the main command index file with caching.

        The index file contains:
        - categories: 7 categories (ball, wall, clump, contact, model, fragment, measure)
        - commands: 115 commands total with metadata
        - python_sdk_alternatives: Command to Python SDK mappings
        - command_patterns: Common command patterns

        Returns:
            Dict containing index data structure

        Raises:
            FileNotFoundError: If index.json doesn't exist

        Example:
            >>> index = CommandLoader.load_index()
            >>> categories = index["categories"]
            >>> len(categories)
            7
            >>> "ball" in categories
            True
        """
        index_path = PFC_COMMAND_DOCS_ROOT / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(f"Command index file not found: {index_path}")

        with open(index_path, encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))

    @staticmethod
    def load_command_doc(category: str, command_name: str) -> dict[str, Any] | None:
        """Load documentation for a specific command.

        Args:
            category: Command category (e.g., "ball", "contact", "model")
            command_name: Command name (e.g., "create", "property", "cycle")

        Returns:
            Command documentation dict with fields:
                - command: Full command name
                - syntax: Command syntax
                - description: Detailed description
                - parameters: Parameter definitions
                - examples: Usage examples
                - notes: Additional notes
                - related_commands: Related commands
                - python_alternative: Python SDK alternative (if available)

            Returns None if command not found.

        Example:
            >>> doc = CommandLoader.load_command_doc("ball", "create")
            >>> doc["syntax"]
            "ball create <keyword> ..."
            >>> "description" in doc
            True
        """
        index = CommandLoader.load_index()

        # Find command file path from index
        categories = index.get("categories", {})
        if category not in categories:
            return None

        category_data = categories[category]
        commands = category_data.get("commands", [])

        # Find matching command
        command_file = None
        for cmd in commands:
            if cmd["name"] == command_name:
                command_file = cmd.get("file")
                break

        if not command_file:
            return None

        # Load command documentation
        doc_path = PFC_COMMAND_DOCS_ROOT / command_file
        if not doc_path.exists():
            return None

        with open(doc_path, encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))

    @staticmethod
    def get_all_commands() -> list[dict[str, Any]]:
        """Get all commands from all categories.

        Returns:
            List of command metadata dicts, each containing:
                - name: Command name
                - category: Category name
                - file: File path
                - short_description: Brief description
                - syntax: Command syntax
                - python_available: Python SDK availability

        Example:
            >>> commands = CommandLoader.get_all_commands()
            >>> len(commands)
            115  # Total across all 7 categories
            >>> commands[0]["category"] in ["ball", "wall", "clump", ...]
            True
        """
        index = CommandLoader.load_index()
        categories = index.get("categories", {})

        all_commands = []
        for category_name, category_data in categories.items():
            for cmd in category_data.get("commands", []):
                all_commands.append({**cmd, "category": category_name})

        return all_commands

    @staticmethod
    def clear_cache() -> None:
        """Clear all cached data.

        Useful for testing or when documentation files are updated.
        """
        CommandLoader.load_index.cache_clear()
