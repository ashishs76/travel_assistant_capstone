import os
import pytest
from dotenv import load_dotenv

load_dotenv()

from ..orchestrator.graph import build_graph
from ..orchestrator.extractor import IncompleteRequestError

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="requires ANTHROPIC_API_KEY"
)


def test_graph_end_to_end_produces_itinerary():
    graph = build_graph()
    final_state = graph.invoke({
        "user_request": "Plan a 2-day trip to Cancun, Mexico for $400, single city"
    })
    print("FINAL ITINERARY:\n", final_state.get("final_itinerary"))
    print("VIOLATIONS:", final_state.get("guardrail_violations"))
    assert final_state.get("final_itinerary") or final_state.get("guardrail_violations")

def test_graph_raises_on_incomplete_request():
    graph = build_graph()
    try:
        graph.invoke({"user_request": "I want to go somewhere nice"})
    except IncompleteRequestError as e:
        print("Correctly caught:", e)

    with pytest.raises(IncompleteRequestError):
        graph.invoke({"user_request": "I want to go somewhere nice"})