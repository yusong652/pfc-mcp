"""PFC Command Browse Tool - Navigate and retrieve command documentation."""

from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from pfc_mcp.contracts import build_docs_data, build_error, build_ok
from pfc_mcp.docs.commands import CommandLoader
from pfc_mcp.utils import normalize_input


def register(mcp: FastMCP):
    """Register pfc_browse_commands tool with the MCP server."""

    @mcp.tool()
    def pfc_browse_commands(
        command: str | None = Field(
            None,
            description=(
                "PFC command to browse (space-separated, matching PFC syntax). Examples:\n"
                "- None or '': List all command categories\n"
                "- 'ball': List all ball commands\n"
                "- 'ball create': Get ball create documentation\n"
                "- 'contact': List all contact commands\n"
                "- 'contact property': Get contact property command documentation"
            ),
        ),
    ) -> dict[str, Any]:
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
            return build_ok(_browse_root())

        parts = cmd.split()

        if len(parts) == 1:
            payload = _browse_category(parts[0])
        else:
            category = parts[0]
            command_name = " ".join(parts[1:])
            payload = _browse_command(category, command_name)
        return _wrap_payload(payload)


def _browse_root() -> dict[str, Any]:
    """Level 0: Return overview of all command categories."""
    index = CommandLoader.load_index()
    categories = index.get("categories", {})
    category_items: list[dict[str, Any]] = []
    total_commands = 0

    for category_name, category_data in categories.items():
        commands = category_data.get("commands", [])
        command_count = len(commands)
        total_commands += command_count
        category_items.append(
            {
                "name": category_name,
                "description": category_data.get("description", ""),
                "command_count": command_count,
            }
        )

    return build_docs_data(
        source="commands",
        action="browse",
        entries=category_items,
        summary={
            "count": len(category_items),
            "total_commands": total_commands,
        },
    )


def _browse_category(category: str) -> dict[str, Any]:
    """Level 1: Return list of commands in a category."""
    index = CommandLoader.load_index()
    categories = index.get("categories", {})

    if category not in categories:
        return {
            "source": "commands",
            "action": "browse",
            "error": {
                "code": "category_not_found",
                "message": f"Category '{category}' not found.",
            },
            "input": {"category": category},
            "available_categories": sorted(categories.keys()),
        }

    cat_data = categories[category]
    commands = cat_data.get("commands", [])
    command_items: list[dict[str, Any]] = []
    for cmd in commands:
        command_items.append(
            {
                "name": cmd.get("name", ""),
                "short_description": cmd.get("short_description", ""),
                "syntax": cmd.get("syntax"),
                "python_available": bool(cmd.get("python_available", False)),
            }
        )

    return build_docs_data(
        source="commands",
        action="browse",
        entries=command_items,
        summary={
            "count": len(command_items),
            "category": category,
            "description": cat_data.get("description", ""),
        },
    )


def _browse_command(category: str, command_name: str) -> dict[str, Any]:
    """Level 2: Return full documentation for a specific command."""
    cmd_doc = CommandLoader.load_command_doc(category, command_name)

    if not cmd_doc:
        index = CommandLoader.load_index()
        categories = index.get("categories", {})

        if category not in categories:
            return {
                "source": "commands",
                "action": "browse",
                "error": {
                    "code": "category_not_found",
                    "message": f"Category '{category}' not found.",
                },
                "input": {"category": category, "command": command_name},
                "available_categories": sorted(categories.keys()),
            }

        cat_data = categories[category]
        commands = cat_data.get("commands", [])
        available_cmds = [cmd.get("name") for cmd in commands]
        return {
            "source": "commands",
            "action": "browse",
            "error": {
                "code": "command_not_found",
                "message": f"Command '{command_name}' not found in '{category}'.",
            },
            "input": {"category": category, "command": command_name},
            "available_commands": available_cmds,
        }

    return build_docs_data(
        source="commands",
        action="browse",
        entries=[
            {
                "category": category,
                "command": command_name,
                "doc": cmd_doc,
            }
        ],
        summary={"count": 1},
    )


def _wrap_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap tool payload into unified envelope."""
    if "error" in payload:
        err = payload.get("error") or {}
        details = {k: v for k, v in payload.items() if k != "error"}
        return build_error(
            code=str(err.get("code") or "browse_error"),
            message=str(err.get("message") or "Browse failed"),
            details=details or None,
        )
    return build_ok(payload)
