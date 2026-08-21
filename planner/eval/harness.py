"""
Eval harness — runs a fixed set of test cases through the graph and
scores structural/behavioral properties. Not a judge of subjective
itinerary quality (that needs a human) — this checks the guarantees
the system is supposed to provide:

  - task success rate: did the graph complete without guardrail violations?
  - citation coverage: did RAG context get retrieved and carried through?
  - weather compliance: for high-rain-probability trips, does the output
    acknowledge a weather-based adjustment?
  - latency: end-to-end wall clock per request

Also includes one ablation (weather removed) to demonstrate that the
weather-compliance guardrail is actually load-bearing, not decorative.
"""

import time
from dotenv import load_dotenv
load_dotenv()

from planner.orchestrator.graph import build_graph
from planner.orchestrator.extractor import IncompleteRequestError

TEST_CASES = [
    # -- complete requests, should succeed --
    {"id": "TC01", "request": "Plan a 3-day trip to Kyoto, Japan for $600, single city"},
    {"id": "TC02", "request": "Plan a 5-day trip to Lisbon, Portugal for $1000, single city"},
    {"id": "TC03", "request": "Plan a 2-day trip to Cancun, Mexico for $400, single city"},
    {"id": "TC04", "request": "Plan a 4-day trip to Rome, Italy for $800, single city"},
    {"id": "TC05", "request": "Plan a day trip to Central Park, New York"},
    {"id": "TC06", "request": "Plan a 3-day trip to Bangkok, Thailand for $300, single city"},
    {"id": "TC07", "request": "Plan a 6-day trip to Barcelona, Spain for $1200, single city"},
    {"id": "TC08", "request": "Plan a 2-day trip to Reykjavik, Iceland for $500, single city"},

    # -- edge cases --
    {"id": "TC09", "request": "Plan a 3-day trip to Marrakech, Morocco for $450, single city"},
    {"id": "TC10", "request": "Plan a 6-day trip visiting Rome and then Florence, budget $1500"},

    # -- deliberately incomplete requests: should raise IncompleteRequestError --
    {"id": "TC11", "request": "I want to go to Lisbon"},
    {"id": "TC12", "request": "Plan a trip for $500"},

    # -- nonsense/unresolvable destination: tests tool-layer failure handling --
    {"id": "TC13", "request": "Plan a 3-day trip to Xyzzyplonkistan for $500, single city"},
]


def run_single_case(case: dict) -> dict:
    graph = build_graph()
    start = time.time()
    result = {
        "id": case["id"],
        "request": case["request"],
        "outcome": None,
        "latency_sec": None,
        "citation_present": False,
        "weather_compliant": None,
        "violations": [],
        "error": None,
    }

    try:
        final_state = graph.invoke({"user_request": case["request"]})
        result["latency_sec"] = round(time.time() - start, 2)

        if final_state.get("final_itinerary"):
            result["outcome"] = "success"
        else:
            result["outcome"] = "guardrail_blocked"
            result["violations"] = final_state.get("guardrail_violations", [])

        result["citation_present"] = bool(final_state.get("rag_context"))

        high_rain_days = [
            d for d in final_state.get("weather", {}).get("days", [])
            if (d.get("precip_probability_pct") or 0) > 50
        ]
        if high_rain_days:
            itinerary_text = (
                final_state.get("final_itinerary")
                or final_state.get("itinerary_raw")
                or ""
            ).lower()
            result["weather_compliant"] = (
                "rain" in itinerary_text or "weather" in itinerary_text
            )

    except IncompleteRequestError as e:
        result["latency_sec"] = round(time.time() - start, 2)
        result["outcome"] = "incomplete_request"  # expected/correct for TC10, TC11
        result["error"] = str(e)

    except Exception as e:
        result["latency_sec"] = round(time.time() - start, 2)
        result["outcome"] = "exception"
        result["error"] = str(e)

    return result


def run_eval_suite(verbose: bool = True) -> list:
    results = [run_single_case(c) for c in TEST_CASES]

    if verbose:
        for r in results:
            print(f"[{r['outcome']!s:>18}] {r['id']}: {r['request'][:60]}  ({r['latency_sec']}s)")

    return results


def run_ablation_no_weather(verbose: bool = True) -> list:
    """Same test cases, but weather_node's output is zeroed out before
    reaching crew_node — isolates whether weather context actually
    changes the guardrail's weather-compliance outcome."""
    import planner.orchestrator.tool_nodes as tool_nodes

    original_weather_node = tool_nodes.weather_node
    tool_nodes.weather_node = lambda state: {"weather": {"days": []}}

    try:
        results = run_eval_suite(verbose=verbose)
    finally:
        tool_nodes.weather_node = original_weather_node  # restore

    return results


def summarize(results: list) -> dict:
    total = len(results)
    successes = sum(1 for r in results if r["outcome"] == "success")
    citation_rate = sum(1 for r in results if r["citation_present"]) / total

    weather_checks = [r for r in results if r["weather_compliant"] is not None]
    weather_compliance_rate = (
        sum(1 for r in weather_checks if r["weather_compliant"]) / len(weather_checks)
        if weather_checks else None
    )

    avg_latency = sum(r["latency_sec"] for r in results if r["latency_sec"] is not None) / total

    return {
        "task_success_rate": round(successes / total, 2),
        "citation_coverage": round(citation_rate, 2),
        "weather_compliance_rate": (
            round(weather_compliance_rate, 2) if weather_compliance_rate is not None else "N/A"
        ),
        "avg_latency_sec": round(avg_latency, 2),
        "total_cases": total,
    }


if __name__ == "__main__":
    print("=== FULL SUITE ===")
    with_weather = run_eval_suite()
    with_weather_summary = summarize(with_weather)
    print("\nSUMMARY (full system):")
    for k, v in with_weather_summary.items():
        print(f"  {k}: {v}")

    print("\n=== ABLATION: NO WEATHER ===")
    without_weather = run_ablation_no_weather()
    without_weather_summary = summarize(without_weather)
    print("\nSUMMARY (no weather ablation):")
    for k, v in without_weather_summary.items():
        print(f"  {k}: {v}")