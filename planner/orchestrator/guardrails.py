"""
Final reliability node: deterministic, non-LLM checks run after the
CrewAI crew produces an itinerary, before it's released as
state["final_itinerary"].

This is the project's reliability/oversight pattern — distinct from
the tool-level failure handling in tool_nodes.py (which logs
violations for *retrieval* failures, e.g. a failed weather/POI call)
in that this node checks the *output* of the whole pipeline, after
generation, regardless of whether every upstream step succeeded. A
tool-level failure and a guardrails-level failure can both land in
guardrail_violations, but they're checking different things: "did the
inputs come through cleanly" vs. "is the generated result acceptable
to ship."

If ANY violation is found (structural or content-based), the guardrail
withholds the itinerary entirely (final_itinerary = None) rather than
returning something known to be flawed — see main.py, which checks
final_itinerary and falls back to printing guardrail_violations when
it's None.

Checks currently implemented:
  1. Itinerary non-empty / not suspiciously short (crude length
     heuristic — catches an obviously broken/truncated crew response,
     not a subtly bad one).
  2. POIs were found at all (if poi_node returned [], the itinerary is
     likely generic/ungrounded rather than reflecting real places).
  3. Weather compliance — if any day has >50% precipitation
     probability, the itinerary text must mention "rain" or "weather"
     somewhere, or it's flagged. This is a proxy for "did the Executor
     agent actually use the weather context it was given," not a
     verification that the SCHEDULE was actually adjusted (e.g. it
     would pass if the text merely says "expect rain" without moving
     any activities indoors) — see docs/architecture.md's discussion
     of weather as a "soft signal made structurally verifiable."

Deliberately NOT implemented (see docs/architecture.md, patterns
excluded): reflection/self-critique. This node checks and blocks, but
never triggers a revision loop back to the crew — a failed guardrail
here is a terminal state for the request, not a retry trigger.
"""

def apply_guardrails(state: dict) -> dict:
    """
    Run all guardrail checks against the crew's output and decide
    whether to release it as the final itinerary.

    Args:
        state: PlannerState. Reads itinerary_raw, pois, weather, and
            any guardrail_violations already logged upstream by
            tool_nodes.py (preserved and appended to, not overwritten).

    Returns:
        {
            "guardrail_violations": [...],  # full accumulated list
            "final_itinerary": str | None,  # None if ANY violation found
        }
    """
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