"""
MCP client: launches interests_mcp_server.py as a stdio subprocess and
calls its search_interests tool.

This is the client half of the project's single MCP integration (see
interests_mcp_server.py and docs/architecture.md, Design Decision #2).
Called by tool_nodes.poi_node() — POI retrieval genuinely goes over
the MCP protocol here, not a direct in-process function call.

KNOWN GAP: this client does not check result.isError before parsing.
If the server-side tool call fails (e.g. Overpass 504 — see
interests.py's retry logic and docs/architecture.md Limitations), the
error text comes back as a single content block that fails JSON
parsing, is silently skipped in the loop below, and call_search_pois()
returns an empty list with no indication anything went wrong. This was
identified and intentionally fixed once already during development
(see project history) but the fix — raising on result.isError — is
not present in this version; only debug print statements referencing
it remain, commented out. Recommend restoring that check before relying
on this in a graded eval run, since an Overpass timeout will currently
look identical to "no POIs found" from the caller's perspective.
"""

import asyncio, sys, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PARAMS = StdioServerParameters(
    command=sys.executable, args=["-m", "planner.tools.interests_mcp_server"],
)

class MCPToolError(Exception):
    """Raised when the MCP server reports a tool-execution error
    (result.isError is True), e.g. an Overpass 504 propagating up from
    interests.search_pois()."""
    pass

async def _call_search_pois_async(place_name, categories="", limit=20):
    """
    Open a stdio connection to the POI MCP server, call its
    search_interests tool, and aggregate the response into a flat list.

    MCP tool results can come back as one or more content blocks (in
    practice, this server has returned either a single JSON array in
    one block, or one block per POI — both are handled here by
    extending vs. appending depending on the parsed type).

    Returns:
        A list of POI dicts. Returns [] if the server call fails or
        the destination yields no POIs — these two cases are NOT
        currently distinguishable by the caller (see module docstring).
    """
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_interests",
                arguments={"place_name": place_name, "categories": categories, "limit": limit},
            )
            if getattr(result, "isError", False):
                error_text = result.content[0].text if result.content else "unknown MCP error"
                raise MCPToolError(f"MCP tool 'search_interests' failed: {error_text}")

            items = []
            for block in result.content:
                if hasattr(block, "text"):
                    try:
                        parsed = json.loads(block.text)
                        if isinstance(parsed, list):
                            items.extend(parsed)
                        else:
                            items.append(parsed)
                    except json.JSONDecodeError as e:
                        continue
            return items


def call_search_pois(place_name: str, categories: str = "", limit: int = 20) -> list:
    """Synchronous wrapper for use inside LangGraph node functions
    (tool_nodes.poi_node), which are not async."""
    return asyncio.run(_call_search_pois_async(place_name, categories, limit))

