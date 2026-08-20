def apply_guardrails(state: dict) -> dict:
    violations = list(state.get("guardrail_violations", []))
    itinerary = state.get("itinerary_raw", "")

    if not itinerary or len(itinerary) < 50:
        violations.append("Itinerary output is empty or suspiciously short.")
    if not state.get("pois"):
        violations.append("No POIs were found — itinerary may be generic/ungrounded.")

    high_rain_days = [d for d in state.get("weather", {}).get("days", [])
                       if (d.get("precip_probability_pct") or 0) > 50]
    if high_rain_days and "rain" not in itinerary.lower() and "weather" not in itinerary.lower():
        violations.append(
            f"{len(high_rain_days)} high-precipitation day(s) detected but itinerary "
            f"doesn't mention any weather-based adjustment."
        )

    final = None if violations else itinerary
    return {"guardrail_violations": violations, "final_itinerary": final}