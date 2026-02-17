"""PFC Python API Query Tool - Keyword search for SDK documentation."""

from typing import Any

from fastmcp import FastMCP

from pfc_mcp.contracts import build_docs_data, build_ok
from pfc_mcp.knowledge.python_api import APIDocFormatter, DocumentationLoader
from pfc_mcp.knowledge.query import APISearch
from pfc_mcp.utils import PythonAPISearchQuery, SearchLimit


def register(mcp: FastMCP) -> None:
    """Register pfc_query_python_api tool with the MCP server."""

    @mcp.tool()
    def pfc_query_python_api(
        query: PythonAPISearchQuery,
        limit: SearchLimit = 10,
    ) -> dict[str, Any]:
        """Search PFC Python SDK documentation by keywords (like grep).

        Returns matching API paths with signatures. Use pfc_browse_python_api for full documentation.

        When to use:
        - You have keywords but don't know exact API path
        - Example: "ball velocity", "create", "contact force"

        Related tools:
        - pfc_browse_python_api: Get full documentation for a known API path
        - pfc_query_command: Search PFC commands by keywords
        """
        matches = APISearch.search(query, top_k=limit)
        results_payload: list[dict[str, Any]] = []
        for result in matches:
            api_path = result.document.name
            sig = APIDocFormatter.format_signature(api_path, result.document.metadata)
            results_payload.append(
                {
                    "api_path": api_path,
                    "signature": sig,
                    "category": result.document.category,
                    "description": result.document.description,
                    "score": result.score,
                    "rank": result.rank,
                    "metadata": result.document.metadata,
                }
            )

        payload: dict[str, Any] = build_docs_data(
            source="python_api",
            action="query",
            entries=results_payload,
            summary={
                "count": len(results_payload),
            },
        )

        if not results_payload:
            index = DocumentationLoader.load_index()
            hints = []
            for hint_key, hint_msg in index.get("fallback_hints", {}).items():
                if hint_key in query.lower():
                    hints.append(hint_msg)
            if hints:
                payload["summary"]["hints"] = hints

        return build_ok(payload)
