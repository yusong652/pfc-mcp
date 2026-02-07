"""PFC Command Query Tool - Keyword search for command documentation."""

from fastmcp import FastMCP

from pfc_mcp.docs.commands import CommandFormatter
from pfc_mcp.docs.query import CommandSearch
from pfc_mcp.utils import SearchQuery, SearchLimit


def register(mcp: FastMCP):
    """Register pfc_query_command tool with the MCP server."""

    @mcp.tool()
    def pfc_query_command(
        query: SearchQuery,
        limit: SearchLimit = 10,
    ) -> str:
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

        if not results:
            return CommandFormatter.format_no_results_response(query)

        result_lines = [f"Found {len(results)} command(s) for '{query}':", ""]

        for result in results:
            title = result.document.title
            category = result.document.category

            cmd_parts = title.split(maxsplit=1)
            cmd_name = cmd_parts[1] if len(cmd_parts) > 1 else title
            browse_path = f"{category} {cmd_name}" if category else title
            result_lines.append(f"- {title}: pfc_browse_commands(command=\"{browse_path}\")")

        result_lines.append("")
        result_lines.append("Use pfc_browse_commands(command=\"...\") for full documentation")

        return "\n".join(result_lines)
