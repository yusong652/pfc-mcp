"""PFC Python API Query Tool - Keyword search for SDK documentation."""

from fastmcp import FastMCP

from pfc_mcp.docs.python_api import DocumentationLoader, APIDocFormatter
from pfc_mcp.docs.query import APISearch
from pfc_mcp.utils import PythonAPISearchQuery, SearchLimit


def register(mcp: FastMCP):
    """Register pfc_query_python_api tool with the MCP server."""

    @mcp.tool()
    def pfc_query_python_api(
        query: PythonAPISearchQuery,
        limit: SearchLimit = 10,
    ) -> str:
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

        if not matches:
            index = DocumentationLoader.load_index()
            hints = []
            for hint_key, hint_msg in index.get("fallback_hints", {}).items():
                if hint_key in query.lower():
                    hints.append(hint_msg)

            return APIDocFormatter.format_no_results_response(query, hints)

        result_lines = [f"Found {len(matches)} API(s) for '{query}':", ""]

        for result in matches:
            api_path = result.document.name
            sig = APIDocFormatter.format_signature(api_path, result.document.metadata)
            if sig:
                result_lines.append(f"- {api_path}: {sig}")
            else:
                result_lines.append(f"- {api_path}")

        result_lines.append("")
        result_lines.append("Use pfc_browse_python_api(api=\"<path>\") for full documentation")

        return "\n".join(result_lines)
