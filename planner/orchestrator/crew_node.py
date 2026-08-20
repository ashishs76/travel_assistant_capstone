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