import asyncio, sys, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PARAMS = StdioServerParameters(
    command=sys.executable, args=["-m", "planner.tools.interests_mcp_server"],
)

async def _call_search_pois_async(place_name, categories="", limit=20):
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_interests",
                arguments={"place_name": place_name, "categories": categories, "limit": limit},
            )
            #print("NUM CONTENT BLOCKS:", len(result.content))
            #print("IS ERROR:", getattr(result, "isError", None))

            items = []
            for block in result.content:
                #print("BLOCK TYPE:", type(block), "HAS TEXT:", hasattr(block, "text"))
                if hasattr(block, "text"):
                    #print("BLOCK TEXT:", repr(block.text))
                    try:
                        parsed = json.loads(block.text)
                        if isinstance(parsed, list):
                            items.extend(parsed)
                        else:
                            items.append(parsed)
                    except json.JSONDecodeError as e:
                        #print("JSON PARSE ERROR:", e)
                        continue
            #print("FINAL ITEMS:", items)
            return items


def call_search_pois(place_name: str, categories: str = "", limit: int = 20) -> list:
    return asyncio.run(_call_search_pois_async(place_name, categories, limit))

