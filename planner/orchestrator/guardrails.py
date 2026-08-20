def apply_guardrails(state: dict) -> dict:
    violations = list(state.get("guardrail_violations", []))
    itinerary = state.get("itinerary_raw", "")

    if not itinerary or len(itinerary) < 50:
        violations.append("Itinerary output is empty or suspiciously short.")

    if not state.get("pois"):
        violations.append("No POIs were found — itinerary may be generic/ungrounded.")

    final = None if violations else itinerary
    return {"guardrail_violations": violations, "final_itinerary": final}