"""
Tests for the CrewAI Planner->Executor crew (crewagents/crew.py).

Guarded with skipif, matching the pattern used in extractor_test.py,
graph_test.py, and wikipedia_rag_test.py — a TA running the full suite
without ANTHROPIC_API_KEY set gets a clean skip here, not an
unconditional live API call with no pass/fail signal.
"""

import os
import pytest
from dotenv import load_dotenv

load_dotenv()

from planner.crewagents.crew import run_travel_crew

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="requires ANTHROPIC_API_KEY"
)

sample_pois = [
    {"name": "Chichen Itza", "category": "attraction"},
    {"name": "Playa Delfines", "category": "attraction"},
    {"name": "La Habichuela Sunset", "category": "restaurant"},
]
sample_weather = {"days": [{"date": "2026-09-01", "temp_max_c": 32, "precip_probability_pct": 40}]}
sample_rag = (
    "Cancun developed rapidly after Mexico's government identified it as a "
    "prime location for tourism in the 1970s, and it is now known for its "
    "beaches along the Caribbean coast and nearby Maya archaeological sites."
)


def test_crew_produces_nonempty_itinerary():
    """
    Smoke test: the crew runs end to end (Planner -> Executor handoff)
    and produces a real, non-trivial itinerary. Does not assert on
    specific content — CrewAI/LLM output is non-deterministic — only
    that the pipeline completes and the output is substantial enough
    to plausibly be a real itinerary, not an empty or truncated response.
    """
    result = run_travel_crew(
        destination="Cancun, Mexico",
        num_days=2,
        pois=sample_pois,
        budget={"total_ceiling_usd": 400, "per_day_ceiling_usd": 200},
        weather=sample_weather,
        rag_facts=sample_rag,
    )

    assert result.raw
    assert len(result.raw) > 100  # not a trivially empty/short response


def test_crew_output_reflects_planner_handoff():
    """
    Weaker, best-effort check that the Executor's output plausibly
    incorporates content from the Planner's skeleton — e.g. at least
    one of the supplied POI names appears somewhere in the final text.
    This is not a strong guarantee (an LLM could paraphrase a POI name
    away entirely) but a reasonable signal that context=[planning_task]
    is actually wiring data through, not just running two disconnected
    calls.
    """
    result = run_travel_crew(
        destination="Cancun, Mexico",
        num_days=2,
        pois=sample_pois,
        budget={"total_ceiling_usd": 400, "per_day_ceiling_usd": 200},
        weather=sample_weather,
        rag_facts=sample_rag,
    )

    poi_names = [p["name"] for p in sample_pois]
    assert any(name in result.raw for name in poi_names), (
        f"Expected at least one of {poi_names} to appear in the itinerary, "
        f"got: {result.raw[:300]}..."
    )