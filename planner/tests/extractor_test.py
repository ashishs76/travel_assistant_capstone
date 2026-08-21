# planner/tests/test_router.py
import os
import pytest
from dotenv import load_dotenv
load_dotenv()

from planner.orchestrator.extractor import extract_trip_details, IncompleteRequestError

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="requires ANTHROPIC_API_KEY"
)

def test_route_extracts_complete_request():
    result = extract_trip_details({"user_request": "Plan a 4-day trip to Lisbon, Portugal for $900"})
    assert "Lisbon" in result["destination"]
    assert result["num_days"] == 4
    assert result["budget_usd"] == 900


def test_route_raises_on_missing_num_days():
    with pytest.raises(IncompleteRequestError) as exc_info:
        extract_trip_details({"user_request": "I want to go to Lisbon"})
    assert "num_days" in exc_info.value.missing_fields


def test_route_budget_is_optional():
    # budget_usd is NOT in _REQUIRED_FIELDS, so this should succeed without it
    result = extract_trip_details({"user_request": "Plan a 3-day trip to Tokyo, single city"})
    assert result["budget_usd"] is None

def test_extract_infers_day_trip_type():
        result = extract_trip_details({"user_request": "Plan a day trip to Central Park, New York"})
        assert result["trip_type"] == "day_trip"

def test_extract_infers_multi_city_type():
        result = extract_trip_details({
            "user_request": "Plan a 6-day trip visiting Rome and then Florence, budget $1500"
        })
        assert result["trip_type"] == "multi_city"