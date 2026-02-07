"""PFC Reference Browse Tool - Navigate syntax elements and model properties."""

from typing import Optional, cast, Dict, Any

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.docs.references import ReferenceLoader, ReferenceFormatter
from pfc_mcp.utils import normalize_input


def register(mcp: FastMCP):
    """Register pfc_browse_reference tool with the MCP server."""

    @mcp.tool()
    def pfc_browse_reference(
        topic: Optional[str] = Field(
            None,
            description=(
                "Reference topic to browse (space-separated path). Examples:\n"
                "- None or '': List all reference categories\n"
                "- 'contact-models': List all contact models\n"
                "- 'contact-models linear': Linear model properties\n"
                "- 'range-elements': Range elements overview (24 elements)\n"
                "- 'range-elements position': Position range syntax\n"
                "- 'range-elements cylinder': Cylinder range syntax\n"
                "- 'range-elements group': Group range syntax"
            )
        )
    ) -> str:
        """Browse PFC reference documentation (syntax elements, model properties).

        References are language elements used within commands, not standalone commands.

        Navigation levels:
        - No topic: All reference categories
        - Category (e.g., "contact-models"): List items in category
        - Full path (e.g., "contact-models linear"): Full documentation

        When to use:
        - Need contact model property names (kn, ks, fric, pb_*)
        - Need range filtering syntax (position, cylinder, group, id)
        - Setting up "contact cmat add model ... property ..." commands
        - Using range filters in any PFC command

        Related tools:
        - pfc_browse_commands: Command syntax (e.g., "ball create")
        - pfc_query_command: Search commands by keywords
        """
        topic_str = normalize_input(topic, lowercase=True)

        if not topic_str:
            return _browse_references_root()

        parts = topic_str.split()
        category = parts[0]

        if len(parts) == 1:
            return _browse_category(category)
        else:
            item = " ".join(parts[1:])
            return _browse_item(category, item)


def _browse_references_root() -> str:
    refs_index = ReferenceLoader.load_index()
    categories = refs_index.get("categories", {})
    return ReferenceFormatter.format_root(categories)


def _browse_category(category: str) -> str:
    refs_index = ReferenceLoader.load_index()
    categories = refs_index.get("categories", {})

    if category not in categories:
        available = ", ".join(categories.keys())
        error_msg = f"Category '{category}' not found. Available: {available}"
        root_content = ReferenceFormatter.format_root(categories)
        return ReferenceFormatter.format_with_error(error_msg, root_content)

    cat_index = cast(Dict[str, Any], ReferenceLoader.load_category_index(category))
    return ReferenceFormatter.format_index(category, cat_index)


def _browse_item(category: str, item: str) -> str:
    item_doc = ReferenceLoader.load_item_doc(category, item)

    if not item_doc:
        items = ReferenceLoader.get_item_list(category)
        available = [i.get("name", "") for i in items]
        error_msg = f"Item '{item}' not found in '{category}'. Available: {', '.join(available[:15])}{'...' if len(available) > 15 else ''}"

        cat_index = ReferenceLoader.load_category_index(category)
        if cat_index:
            category_content = ReferenceFormatter.format_index(category, cat_index)
            return ReferenceFormatter.format_with_error(error_msg, category_content)
        else:
            refs_index = ReferenceLoader.load_index()
            categories = refs_index.get("categories", {})
            root_content = ReferenceFormatter.format_root(categories)
            return ReferenceFormatter.format_with_error(error_msg, root_content)

    if category == "contact-models":
        return ReferenceFormatter.format_contact_model(item_doc)
    elif category == "range-elements":
        return ReferenceFormatter.format_range_element(item_doc)
    else:
        return f"Category '{category}' not yet implemented"
