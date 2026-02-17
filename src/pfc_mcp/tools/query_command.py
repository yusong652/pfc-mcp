"""PFC Command Query Tool - Keyword search for command documentation."""

from typing import Any

from fastmcp import FastMCP

from pfc_mcp.contracts import build_docs_data, build_ok
from pfc_mcp.knowledge.commands import CommandLoader
from pfc_mcp.knowledge.query import CommandSearch
from pfc_mcp.utils import SearchLimit, SearchQuery


def register(mcp: FastMCP) -> None:
    """Register pfc_query_command tool with the MCP server."""

    @mcp.tool()
    def pfc_query_command(
        query: SearchQuery,
        limit: SearchLimit = 10,
    ) -> dict[str, Any]:
        """Search PFC command documentation by keywords (like grep).

        Returns matching command paths. Use pfc_browse_commands for full documentation.

        When to use:
        - You have keywords but don't know exact command path
        - Example: "ball create", "contact property", "model solve"

        Related tools:
        - pfc_browse_commands: Get full documentation for a known command path
        - pfc_browse_reference: Browse reference docs (e.g., "contact-models linear")
        - pfc_query_python_api: Search Python SDK by keywords
        """
        results = CommandSearch.search_commands_only(query, top_k=limit)
        matches: list[dict[str, Any]] = []
        for result in results:
            metadata = result.document.metadata or {}
            matches.append(
                {
                    "path": result.document.title,
                    "name": result.document.name,
                    "category": result.document.category,
                    "syntax": result.document.syntax,
                    "short_description": metadata.get("short_description"),
                    "score": result.score,
                    "rank": result.rank,
                }
            )

        payload: dict[str, Any] = build_docs_data(
            source="commands",
            action="query",
            entries=matches,
            summary={
                "count": len(matches),
            },
        )

        if not matches:
            categories = sorted(CommandLoader.load_index().get("categories", {}).keys())
            payload["summary"]["hints"] = [
                "Try broader keywords (for example: create, property, solve).",
                "Try category + action (for example: ball create, contact property).",
            ]
            payload["summary"]["available_categories"] = categories

        return build_ok(payload)
