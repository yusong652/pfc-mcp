"""PFC Command Browse Tool - Navigate and retrieve command documentation."""

from typing import Optional

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.docs.commands import CommandLoader, CommandFormatter
from pfc_mcp.utils import normalize_input


def register(mcp: FastMCP):
    """Register pfc_browse_commands tool with the MCP server."""

    @mcp.tool()
    def pfc_browse_commands(
        command: Optional[str] = Field(
            None,
            description=(
                "PFC command to browse (space-separated, matching PFC syntax). Examples:\n"
                "- None or '': List all command categories\n"
                "- 'ball': List all ball commands\n"
                "- 'ball create': Get ball create documentation\n"
                "- 'contact': List all contact commands\n"
                "- 'contact property': Get contact property command documentation"
            )
        )
    ) -> str:
        """Browse PFC command documentation by path (like glob + cat).

        Navigation levels:
        - No command: All 7 categories overview
        - Category only (e.g., "ball"): List commands in category
        - Full command (e.g., "ball create"): Full documentation

        When to use:
        - You know the command category or exact command
        - You want to explore available commands

        Related tools:
        - pfc_query_command: Search commands by keywords (when path unknown)
        - pfc_browse_reference: Browse reference docs (e.g., "contact-models linear")
        """
        cmd = normalize_input(command)

        if not cmd:
            return _browse_root()

        parts = cmd.split()

        if len(parts) == 1:
            return _browse_category(parts[0])
        else:
            category = parts[0]
            command_name = " ".join(parts[1:])
            return _browse_command(category, command_name)


def _browse_root() -> str:
    """Level 0: Return overview of all command categories."""
    index = CommandLoader.load_index()
    categories = index.get("categories", {})
    return CommandFormatter.format_root(categories)


def _browse_category(category: str) -> str:
    """Level 1: Return list of commands in a category."""
    index = CommandLoader.load_index()
    categories = index.get("categories", {})

    if category not in categories:
        available = ", ".join(categories.keys())
        error_msg = f"Category '{category}' not found. Available: {available}"
        root_content = CommandFormatter.format_root(categories)
        return CommandFormatter.format_with_error(error_msg, root_content)

    cat_data = categories[category]
    return CommandFormatter.format_category(category, cat_data)


def _browse_command(category: str, command_name: str) -> str:
    """Level 2: Return full documentation for a specific command."""
    cmd_doc = CommandLoader.load_command_doc(category, command_name)

    if not cmd_doc:
        index = CommandLoader.load_index()
        categories = index.get("categories", {})

        if category not in categories:
            available_cats = ", ".join(categories.keys())
            error_msg = f"Category '{category}' not found. Available: {available_cats}"
            root_content = CommandFormatter.format_root(categories)
            return CommandFormatter.format_with_error(error_msg, root_content)

        cat_data = categories[category]
        commands = cat_data.get("commands", [])
        available_cmds = [cmd.get("name") for cmd in commands]
        error_msg = (
            f"Command '{command_name}' not found in '{category}'. "
            f"Available: {', '.join(available_cmds[:10])}{'...' if len(available_cmds) > 10 else ''}"
        )
        category_content = CommandFormatter.format_category(category, cat_data)
        return CommandFormatter.format_with_error(error_msg, category_content)

    return CommandFormatter.format_command(cmd_doc, category)
