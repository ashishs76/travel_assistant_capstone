"""
Builds and wires the LangGraph StateGraph — the executable form of the
system architecture diagram in docs/architecture.md. If this file and
that diagram ever diverge, this file is the source of truth; the
diagram should be regenerated from here (see
g.get_graph().draw_mermaid(), used to produce the current diagram).

Node-to-file map:
    extract     -> extractor.extract_trip_details   (structured extraction via Claude)
    weather     -> tool_nodes.weather_node           (Open-Meteo, direct call)
    poi         -> tool_nodes.poi_node               (OSM, via MCP server/client)
    rag         -> rag_node.retrieve_node            (Wikipedia, grounds itinerary narrative)
    crew        -> crew_node.crew_node               (CrewAI Planner->Executor, single opaque node)
    guardrails  -> guardrails.apply_guardrails        (deterministic final checks)

Edge structure (control flow):
    extract fans out to weather and poi in parallel — LangGraph runs
    both concurrently since neither depends on the other's output,
    both only need state["destination"]/state["num_days"] which
    extract has already populated. This is the project's
    parallelization pattern (see docs/architecture.md).

    rag currently has TWO incoming edges (from weather AND poi), which
    means LangGraph will not run rag until BOTH parallel branches have
    completed — even though rag only needs state["destination"], which
    was already available right after extract. This is a known
    inefficiency: rag has no actual data dependency on weather or poi,
    so it could instead be added to the same parallel fan-out
    (extract -> rag, alongside extract -> weather and extract -> poi)
    to shave the weather/POI round-trip time off every request's
    latency. Left as-is for now (see docs/architecture.md, noted as a
    known limitation / future optimization) rather than changed, to
    avoid the fan-in complexity of crew needing to wait on three
    branches instead of two.

    crew and guardrails run strictly sequentially after rag — crew
    genuinely depends on weather/poi/rag_context all being present
    (see crew_node.py), and guardrails genuinely depends on crew's
    output, so no further parallelization opportunity exists past rag.

No conditional edges (add_conditional_edges) are used anywhere in this
graph — every request follows the identical static path regardless of
content. There is no branching/routing logic based on, e.g.,
trip_type (extracted by extractor.py but not consumed here or in
crew_node.py — see docs/architecture.md, known gap).

Reflection/revision loops (e.g. crew -> guardrails -> back to crew on
failure) are deliberately NOT implemented — a guardrail violation is
a terminal state (final_itinerary = None), not a retry trigger. See
docs/architecture.md's "patterns deliberately excluded" section for
the reasoning.
"""
from langgraph.graph import StateGraph, END

from .planner_state import PlannerState
from . import extractor, tool_nodes, rag_node, crew_node
from . import guardrails

def build_graph():
    g = StateGraph(PlannerState)

    g.add_node("extract", extractor.extract_trip_details)
    g.add_node("weather", tool_nodes.weather_node)
    g.add_node("poi", tool_nodes.poi_node)
    g.add_node("rag", rag_node.retrieve_node)
    g.add_node("crew", crew_node.crew_node)
    g.add_node("guardrails", guardrails.apply_guardrails)

    g.set_entry_point("extract")

    g.add_edge("extract", "weather")
    g.add_edge("extract", "poi")
    g.add_edge("weather", "rag")
    g.add_edge("poi", "rag")
    g.add_edge("rag", "crew")
    g.add_edge("crew", "guardrails")
    g.add_edge("guardrails", END)

    return g.compile()