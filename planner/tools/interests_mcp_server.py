"""
MCP server: exposes the POI (points-of-interest) tool over the Model
Context Protocol, using stdio transport.

This is the server half of the project's single MCP integration —
chosen specifically for POI retrieval rather than weather, since POI
is the tool most likely to swap data providers later (see
docs/architecture.md, Design Decision #2, for the full justification).

Run standalone (for manual inspection/debugging):
    python -m planner.tools.interests_mcp_server

In the production pipeline, this is launched as a subprocess by
interest_mcp_client.py, not invoked directly — tool_nodes.poi_node()
calls into the client, which talks to this server over the protocol.

Known issue: importing this module (directly or transitively, e.g. via
the client subprocess) triggers a pydantic_settings
IncompleteFieldDefinitionWarning related to FastMCP's internal
`lifespan` field. This is a library-internal warning, not caused by
anything in this file, and does not affect functionality.
"""

from mcp.server.fastmcp import FastMCP
from . import interests

mcp = FastMCP("interest-server")


@mcp.tool()
def search_interests(place_name: str, categories: str = "", limit: int = 20) -> list:
    """
    MCP tool: search OpenStreetMap for points of interest near a place.

    Thin wrapper around interests.search_pois() — see that module for
    the actual Nominatim/Overpass retrieval logic, retry behavior, and
    the current park-only category scoping.

    Args:
        place_name: destination name, e.g. "Kyoto, Japan".
        categories: comma-separated category names (currently only
            "park" is a recognized key in interests.CATEGORY_TAGS — see
            that module for why). Empty string means "all recognized
            categories" (currently just park). Unrecognized category
            names are silently dropped downstream, not here.
        limit: maximum number of POIs to return.

    Returns:
        A list of POI dicts (see interests.search_pois() return docs).
        Note: MCP serializes this return value into one or more content
        blocks in the response — interest_mcp_client.py is responsible
        for reassembling them back into a single flat list.
    """
    cats = [c.strip() for c in categories.split(",") if c.strip()] or None
    return interests.search_pois(place_name, categories=cats, limit=limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")