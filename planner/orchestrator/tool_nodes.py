from ..tools import weather as weather_tool
from ..tools import interest_mcp_client as mcp_client


def weather_node(state: dict) -> dict:
    try:
        forecast = weather_tool.get_forecast(state["destination"], state["num_days"])
    except Exception as e:
        forecast = {"error": str(e), "days": []}
    return {"weather": forecast}


def poi_node(state: dict) -> dict:
    try:
        pois = mcp_client.call_search_pois(state["destination"], limit=15)
    except Exception as e:
        pois = []
        state.setdefault("guardrail_violations", []).append(f"POI MCP call failed: {e}")
    return {"pois": pois}