"""
Extraction node: uses Claude directly (no tool-use/function-calling
features — see docs/architecture.md for why this was deliberately kept
provider-agnostic in pattern even though the current SDK call is
Anthropic-specific) to pull structured trip details out of the user's
free-text request.

This is the entry point of the graph (see orchestrator/graph.py) and
the source of the project's human-in-the-loop behavior: if required
fields can't be extracted, IncompleteRequestError is raised rather
than retried against the LLM or silently defaulted — the user, not
the model, is treated as the authority on missing trip details.

Known gap: _call_claude has no error handling around the Anthropic API
call or the JSON parse. A malformed response (Claude ignoring the
"JSON only" instruction) raises json.JSONDecodeError; an API failure
(rate limit, network, auth) raises an anthropic SDK exception — both
propagate unhandled out of extract_trip_details, distinct from the
designed IncompleteRequestError path, and are not currently retried.
"""
import json
import re
from typing import Optional
import anthropic
from pydantic import BaseModel, ValidationError
from .. import config


class TripRequest(BaseModel):
    """Structured trip request, as extracted by Claude from free text.
    All fields are Optional at the model level — validity (which
    fields are actually required) is enforced separately by
    _REQUIRED_FIELDS in extract_trip_details, not by this schema."""
    destination: Optional[str] = None
    num_days: Optional[int] = None
    budget_usd: Optional[float] = None
    trip_type: Optional[str] = None


class IncompleteRequestError(Exception):
    """
    Raised when the user's request is missing required trip details
    (see _REQUIRED_FIELDS). This is the designed human-in-the-loop
    path: rather than the LLM guessing or being retried with the same
    ambiguous input, the caller (main.py) is expected to catch this
    and surface e's message directly to the user, asking them to
    rewrite their request.

    Attributes:
        missing_fields: list of field names that were null/missing.
        partial: the TripRequest with whatever fields WERE extracted,
            in case a caller wants to show the user what was
            understood so far.
    """
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
    '"trip_type": "single_city" | "multi_city" | "day_trip" or null}\n\n'
    "Guidance for trip_type:\n"
    '- "day_trip" if the trip is a single day with no overnight stay\n'
    '- "multi_city" if the request mentions more than one distinct city/destination, '
    'or phrases like "and then", "followed by", multiple places joined by commas/and\n'
    '- "single_city" if it\'s a multi-day trip centered on one destination\n'
    "Infer trip_type from context when reasonable (e.g. a 1-day request implies "
    '"day_trip" even if not stated explicitly). Use null only if genuinely ambiguous. '
    "Use null for destination, num_days, or budget_usd only if not clearly stated — "
    "do not guess those."
)

_REQUIRED_FIELDS = ["destination", "num_days", "trip_type"]  # budget_usd is optional


def _call_claude(user_request: str) -> dict:
    """
    Send the user's request to Claude and parse its JSON response.

    Strips markdown code fences defensively, since models sometimes
    wrap JSON in ```json blocks despite being told not to.

    Returns:
        The parsed JSON dict, shape matching TripRequest's fields.

    Raises:
        anthropic.* exceptions: on API failure (not caught/retried here).
        json.JSONDecodeError: if Claude's response isn't valid JSON
            after fence-stripping (not caught/retried here — see
            module docstring's Known gap).
    """
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
    """
    LangGraph entry node: extract structured trip details from
    state["user_request"].

    Args:
        state: PlannerState; reads state["user_request"] (the raw
            free-text request).

    Returns:
        {"destination": str, "num_days": int, "budget_usd": float|None,
         "trip_type": str} — all required fields guaranteed non-null
        (validated below); budget_usd may still be None.

    Raises:
        IncompleteRequestError: if any of _REQUIRED_FIELDS came back
            null from Claude's extraction — see that class's docstring.
        json.JSONDecodeError / anthropic.* exceptions: on malformed
            response or API failure — see _call_claude's docstring and
            this module's Known gap.
    """
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