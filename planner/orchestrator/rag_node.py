"""
LangGraph adapter node wrapping the Wikipedia RAG retriever.

Thin translation layer: takes state["destination"], calls
retriever.retrieve_destination_context() (see rag/retriever.py for the
actual Wikipedia fetch, its citation fields, and known gaps —
particularly the title-matching issue where country-suffixed
destination strings like "Kyoto, Japan" may fail to match Wikipedia's
actual page title), and writes the result to state["rag_context"].

This is the node that establishes the project's RAG pattern: the facts
retrieved here are later joined into a single string by crew_node.py
and handed to the CrewAI Executor agent, whose task instructs it to
paraphrase (never quote) them into the itinerary's welcome note. The
grounding claim rests specifically on this citation trail
(source_title/source_url) flowing through to the final output — see
docs/architecture.md for the distinction between this (RAG, cites a
verifiable source) and the weather/POI tools (structured data, no
citation concept).

Runs sequentially after weather_node and poi_node complete (both must
finish before this node runs — see orchestrator/graph.py's edges),
even though it doesn't actually depend on either's output. This is
worth flagging as a possible future optimization: rag_node could run
in parallel with the weather/POI fan-out instead of waiting on it,
since destination is available immediately after extraction.

Known gap: does not currently check for or log a failure/empty case.
If retrieve_destination_context() returns [] (page not found, request
failed, or the title-matching bug above), this node silently passes
along an empty rag_context with no guardrail_violations entry —
unlike weather_node and poi_node, which now log violations on failure
(see tool_nodes.py). Nothing downstream currently verifies whether the
itinerary's welcome note is actually grounded in the retrieved fact
versus the LLM's own training-data knowledge of the destination — see
project discussion on RAG grounding verification.
"""

from ..rag import destination_retriever


def retrieve_node(state: dict) -> dict:
    """
    Fetch RAG context for the current destination and write it to state.

    Args:
        state: PlannerState; reads state["destination"] (must already
            be set by extract_trip_details() — this node assumes
            extraction has already succeeded).

    Returns:
        {"rag_context": [...]} — a list of at most one dict with
        fact/source_title/source_url, or an empty list if no Wikipedia
        page was found or matched (see module docstring re: known gaps).
    """
    context = destination_retriever.retrieve_destination_context(state["destination"])
    return {"rag_context": context}