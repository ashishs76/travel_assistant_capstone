"""
Shared graph state — the LangGraph "shared workspace."

PlannerState is a TypedDict, not a class with methods; LangGraph passes
the accumulated dict to every node function and merges each node's
returned dict back into it. Because total=False, no field is required
to be present at every point in the graph's execution — nodes should
use state.get(key, default) rather than direct indexing when reading
fields that may not have been populated yet by an earlier node,
except where a node's own contract guarantees a field exists (e.g.
weather_node and poi_node can safely assume state["destination"] is
set, since extract_trip_details always runs first and either sets it
or raises before returning).

This file is intentionally a plain data schema with no logic — it
exists purely so every node's inputs/outputs are typed and
inspectable in one place, rather than scattered as implicit dict-key
conventions across orchestrator/*.py.
"""
from typing import TypedDict, List, Dict, Any, Optional

class PlannerState(TypedDict, total=False):
    # input
    user_request: str
    destination: str
    num_days: int
    budget_usd: Optional[float]

    trip_type: str

    # tool outputs (parallel)
    weather: Dict[str, Any]
    pois: List[Dict[str, Any]]

    # RAG
    rag_context: List[Dict[str, str]]

    # crew output
    itinerary_raw: str

    # guardrails
    guardrail_violations: List[str]
    final_itinerary: Optional[str]