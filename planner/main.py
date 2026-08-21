"""
CLI demo entrypoint — interactive, intended for the recorded demo.

Usage:
    python -m planner.main

Prompts the user for a trip request via stdin, runs it through the
full LangGraph pipeline (build_graph()), and prints the result.

load_dotenv() is called immediately, before the graph/extractor
imports below — this ordering is required, not incidental. config.py
reads ANTHROPIC_API_KEY from the environment at import time, and
Python only evaluates an import once per process; if
planner.orchestrator.graph (which transitively imports config.py) were
imported before load_dotenv() ran, ANTHROPIC_API_KEY would already be
cached as empty and no later load_dotenv() call would fix it. (This
exact class of bug — .env loaded too late relative to config.py's
import — was hit and fixed during development; see project history.)

Handles the two distinct "no itinerary" cases differently, matching
how the rest of the pipeline distinguishes them:
  - IncompleteRequestError (raised by extract_trip_details before the
    graph even reaches the parallel fan-out): printed directly and the
    function returns early. This is the human-in-the-loop path — the
    user is expected to rerun with a more complete request.
  - guardrail_violations (graph ran to completion, but guardrails.py
    withheld the result): itinerary is None but final_state still has
    everything else (destination, weather, pois, etc.) — printed as a
    violations list rather than a hard stop, since this is a
    "the system worked correctly and caught a problem" outcome, not a
    crash.

Does NOT currently catch exceptions from crew_node.py or its
downstream CrewAI/Anthropic calls (see crew_node.py's docstring,
Known gap) — an unhandled exception there will surface as a raw
Python traceback on screen rather than a clean message. Worth being
aware of this if it happens during a live demo recording; consider
wrapping the graph.invoke() call in a broader except Exception as a
demo-safety net, separate from fixing the underlying gap in
crew_node.py itself.

Prints trip_type as part of the DETAILS block even though nothing
downstream currently branches on it (see planner_state.py,
docs/architecture.md re: this known gap) — shown here mainly so a demo
viewer can see the extractor correctly inferred it, as evidence the
extraction pattern works, even though the value itself isn't yet
consequential to the itinerary produced.

Citations are only printed if rag_context has at least one entry with
a source_url — if destination_retriever.py's title-matching gap caused an empty
rag_context (see rag/retriever.py's docstring), this section is
silently omitted rather than noting that RAG grounding was attempted
but failed. Worth testing this file against a destination string shape
known to trigger that gap (e.g. "Kyoto, Japan") before relying on the
CITATIONS section reliably appearing during the demo.
"""
from dotenv import load_dotenv

load_dotenv()  # must be called before config.py is imported anywhere below,
                # since config.py reads ANTHROPIC_API_KEY from the environment

from planner.orchestrator.graph import build_graph
from planner.orchestrator.extractor import IncompleteRequestError


def main():
    request = input("Where would you like to go? Describe your trip: ").strip()

    if not request:
        print("No request entered. Exiting.")
        return

    print(f"\nRequest: {request}\n")

    graph = build_graph()

    try:
        final_state = graph.invoke({"user_request": request})
    except IncompleteRequestError as e:
        print(str(e))
        return

    if final_state.get("final_itinerary"):
        print("=== FINAL ITINERARY ===")
        print(final_state["final_itinerary"])
    else:
        print("=== ITINERARY WITHHELD — GUARDRAIL VIOLATIONS ===")
        for v in final_state.get("guardrail_violations", []):
            print(f"  - {v}")

    print("\n=== DETAILS ===")
    print(f"Destination: {final_state.get('destination')}")
    print(f"Trip type:   {final_state.get('trip_type')}")
    print(f"Days:        {final_state.get('num_days')}")
    print(f"Budget:      {final_state.get('budget_usd')}")

    citations = [
        f"{c.get('source_title')}: {c.get('source_url')}"
        for c in final_state.get("rag_context", []) if c.get("source_url")
    ]
    if citations:
        print("\n=== CITATIONS ===")
        for c in citations:
            print(f"  - {c}")


if __name__ == "__main__":
    main()