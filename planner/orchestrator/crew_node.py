"""
LangGraph adapter node wrapping the CrewAI Planner->Executor crew.

This is the architectural seam described in docs/architecture.md,
Design Decision #1: from LangGraph's perspective, this is ONE node —
everything CrewAI does internally (two agents, an explicit task
handoff via context=[planning_task] in crewagents/tasks.py, however
many LLM round-trips the crew needs) is invisible to the graph. This
is where the project's multi-agent pattern actually lives, even though
graph.py only sees a single opaque step.

Aggregates state into the plain-argument shape run_travel_crew()
expects:
  - rag_facts: joins all retrieved facts (see rag_node.py) into a
    single string. Note: if rag_context has more than one fact dict in
    the future, this concatenation has no separator handling beyond a
    single space — currently harmless since retriever.py only ever
    returns 0 or 1 facts, but would need revisiting if that changes.
  - budget: falls back to a default of $250/day * num_days if
    state["budget_usd"] is None (extractor.py deliberately treats
    budget as optional — see that module).
  - pois / weather: passed through as-is; if either tool failed
    upstream (see tool_nodes.py), this receives an empty list / a
    dict with an "error" key respectively, and the crew proceeds
    anyway rather than short-circuiting — the crew has no awareness
    that an upstream tool failed, only that pois/weather look sparse
    or empty. Whether this degrades gracefully (crew writes a
    generic itinerary) or produces confusing output depends entirely
    on how the Planner/Executor agents' prompts (crewagents/tasks.py)
    handle empty inputs, which is not currently tested explicitly.

Known gap: no error handling around run_travel_crew() itself. If the
crew raises (e.g. a CrewAI internal error, an Anthropic API failure
mid-crew, or a malformed result.raw), the exception propagates
unhandled out of this node and crashes graph.invoke() — unlike
weather_node/poi_node, which both catch and degrade gracefully. This
is a real gap given crew_node is the single most complex, LLM-call-
heavy step in the pipeline and therefore statistically the most likely
node to fail; a caught crew failure currently produces no
guardrail_violations entry and no graceful degradation, only a crashed
run landing in the eval harness's generic "exception" outcome bucket.
"""

from ..crewagents.crew import run_travel_crew

def crew_node(state: dict) -> dict:
    rag_facts = " ".join(c.get("fact", "") for c in state.get("rag_context", []))

    budget_ceiling = state.get("budget_usd") or 250 * state["num_days"]

    result = run_travel_crew(
        destination=state["destination"],
        num_days=state["num_days"],
        pois=state.get("pois", []),
        budget={
            "total_ceiling_usd": budget_ceiling,
            "per_day_ceiling_usd": budget_ceiling / state["num_days"],
        },
        weather=state.get("weather", {}),
        rag_facts=rag_facts,
    )
    return {"itinerary_raw": result.raw}