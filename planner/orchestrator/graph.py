from langgraph.graph import StateGraph, END

from .planner_state import PlannerState
from . import request_router, tool_nodes, rag_node, crew_node
from . import guardrails

def build_graph():
    g = StateGraph(PlannerState)

    g.add_node("router", request_router.route)
    g.add_node("weather", tool_nodes.weather_node)
    g.add_node("poi", tool_nodes.poi_node)
    g.add_node("rag", rag_node.retrieve_node)
    g.add_node("crew", crew_node.crew_node)
    g.add_node("guardrails", guardrails.apply_guardrails)

    g.set_entry_point("router")

    g.add_edge("router", "weather")
    g.add_edge("router", "poi")
    g.add_edge("weather", "rag")
    g.add_edge("poi", "rag")
    g.add_edge("rag", "crew")
    g.add_edge("crew", "guardrails")
    g.add_edge("guardrails", END)

    return g.compile()