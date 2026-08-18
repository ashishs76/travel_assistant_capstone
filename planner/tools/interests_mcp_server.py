from mcp.server.fastmcp import FastMCP
from . import interests

mcp = FastMCP("interest-server")


@mcp.tool()
def search_interests(place_name: str, categories: str = "", limit: int = 20) -> list:
    """Search OpenStreetMap for points of interest near a place."""
    cats = [c.strip() for c in categories.split(",") if c.strip()] or None
    return interests.search_pois(place_name, categories=cats, limit=limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")