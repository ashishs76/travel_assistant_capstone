
import json
import re
from typing import Optional
import anthropic
from pydantic import BaseModel, ValidationError
from .. import config


class TripRequest(BaseModel):
    destination: Optional[str] = None
    num_days: Optional[int] = None
    budget_usd: Optional[float] = None
    trip_type: Optional[str] = None


class IncompleteRequestError(Exception):
    """Raised when the user's request is missing required trip details."""
    def __init__(self, missing_fields: list, partial: TripRequest):
        self.missing_fields = missing_fields
        self.partial = partial
        super().__init__(
            f"Your request is missing: {', '.join(missing_fields)}. "
            f"Please rewrite your request to include this information."
        )


_SYSTEM = (
    "Extract trip details from the traveler's request. "
    "Respond with ONLY a JSON object — no prose, no markdown code fences — "
    "matching exactly this shape:\n"
    '{"destination": string or null, "num_days": integer or null, '
    '"budget_usd": number or null, '
    '"trip_type": "single_city" | "multi_city" | "day_trip" or null}\n'
    "Use null for any field not clearly stated in the request. Do not guess or infer defaults."
)

_REQUIRED_FIELDS = ["destination", "num_days", "trip_type"]  # budget_usd is optional


def _call_claude(user_request: str) -> dict:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=300,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_request}],
    )
    raw = "".join(b.text for b in response.content if b.type == "text")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    return json.loads(cleaned)


def extract_trip_details(state: dict) -> dict:
    text = state["user_request"]

    data = _call_claude(text)
    trip = TripRequest(**data)

    missing = [f for f in _REQUIRED_FIELDS if getattr(trip, f) is None]
    if missing:
        raise IncompleteRequestError(missing, trip)

    return {
        "destination": trip.destination,
        "num_days": trip.num_days,
        "budget_usd": trip.budget_usd,
        "trip_type": trip.trip_type,
    }