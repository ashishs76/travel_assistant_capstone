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
    anyway rather than short-circuiting.

Error handling: any exception from run_travel_crew() (a CrewAI
internal error, an Anthropic API failure mid-crew, a malformed
result.raw, etc.) is caught here, matching the pattern already used in
tool_nodes.py's weather_node/poi_node — logged to
guardrail_violations rather than propagating unhandled and crashing
graph.invoke(). itinerary_raw is set to an empty string on failure,
which guardrails.py's existing "empty or suspiciously short" check
then catches downstream, so a crew failure correctly results in
final_itinerary = None with a clear, attributed violation message,
rather than an unhandled exception landing in the eval harness's
generic "exception" outcome bucket.
"""

from ..crewagents.crew import run_travel_crew


def crew_node(state: dict) -> dict:
    rag_facts = " ".join(c.get("fact", "") for c in state.get("rag_context", []))

    budget_ceiling = state.get("budget_usd") or 250 * state["num_days"]

    try:
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
    except Exception as e:
        violations = list(state.get("guardrail_violations", []))
        violations.append(f"Crew execution failed: {e}")
        return {"itinerary_raw": "", "guardrail_violations": violations}