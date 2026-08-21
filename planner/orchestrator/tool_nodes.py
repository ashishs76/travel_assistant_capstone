"""
LangGraph adapter nodes wrapping the weather and POI tools.

These are thin translation layers: each function takes/returns
PlannerState (dict) as required by LangGraph's node interface, and
internally calls the already-tested tool modules (tools/weather.py,
tools/interest_mcp_client.py) with plain arguments. No retrieval logic
lives here — only state plumbing and failure handling.

Both nodes run in parallel in the graph (see orchestrator/graph.py):
extract_trip_details() fans out to weather_node and poi_node
simultaneously, and rag_node waits for both to complete before running.
This is the project's control-flow/parallelization pattern.

Both nodes degrade gracefully on failure (empty result rather than a
crashed graph) and log a guardrail_violations entry, so a tool failure
is visible to guardrails.py and the eval harness rather than silently
looking identical to "nothing found." Node functions return updates
rather than mutating the input state dict, matching LangGraph's
expected node contract.
"""
from ..tools import weather as weather_tool
from ..tools import interest_mcp_client as mcp_client


def weather_node(state: dict) -> dict:
    """
    Fetch a weather forecast for state["destination"]/state["num_days"].

    Degrades gracefully on failure: any exception from weather.py
    (geocoding failure, Open-Meteo HTTP error — see that module's
    docstring re: no retry logic) results in an empty forecast rather
    than crashing the graph, and is logged to
    state["guardrail_violations"] so the failure is visible downstream
    rather than silently looking like "no precipitation data."

    Returns:
        {"weather": {...}} on success, or
        {"weather": {"error": str, "days": []}, "guardrail_violations": [...]}
        on failure — the violations list includes any prior entries
        already in state, plus this node's new one.
    """
    try:
        forecast = weather_tool.get_forecast(state["destination"], state["num_days"])
        return {"weather": forecast}
    except Exception as e:
        violations = list(state.get("guardrail_violations", []))
        violations.append(f"Weather lookup failed: {e}")
        return {"weather": {"error": str(e), "days": []}, "guardrail_violations": violations}

def poi_node(state: dict) -> dict:
    """
    Fetch points of interest for state["destination"] via the POI MCP
    client (interest_mcp_client.py), which launches
    interests_mcp_server.py as a subprocess.

    Catches interest_mcp_client.MCPToolError specifically — raised
    when the MCP server reports a tool-execution error (e.g. an
    Overpass 504 propagating from interests.search_pois()), now
    distinguishable from a successful call that simply found no POIs.
    A broader Exception catch remains as a fallback for failures
    outside the MCP protocol itself (e.g. subprocess launch failure).

    Returns:
        {"pois": [...]} on success, or
        {"pois": [], "guardrail_violations": [...]} on failure —
        same accumulation pattern as weather_node above.
    """
    try:
        pois = mcp_client.call_search_pois(state["destination"], limit=15)
        return {"pois": pois}
    except (mcp_client.MCPToolError, Exception) as e:
        violations = list(state.get("guardrail_violations", []))
        violations.append(f"POI MCP call failed: {e}")
        return {"pois": [], "guardrail_violations": violations}