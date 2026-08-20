from typing import TypedDict, List, Dict, Any, Optional

class PlannerState(TypedDict, total=False):
    # input
    user_request: str
    destination: str
    num_days: int
    budget_usd: Optional[float]

    # routing
    trip_type: str

    # tool outputs (parallel)
    weather: Dict[str, Any]
    pois: List[Dict[str, Any]]

    # RAG
    rag_context: List[Dict[str, str]]

    # crew output
    itinerary_raw: str

    # guardrails
    guardrail_violations: List[str]
    final_itinerary: Optional[str]