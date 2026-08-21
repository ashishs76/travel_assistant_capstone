"""
RAG retriever — grounds destination background in Wikipedia, with citations.

Data source: Wikipedia REST API (public, keyless) — specifically the
page-summary endpoint (https://en.wikipedia.org/api/rest_v1/page/summary/{title}),
chosen over the full Wikipedia action API for simplicity: one request
returns exactly what's needed (a short extract, a title, and a
ready-made citation URL) with no wikitext parsing required.

Called by rag_node.retrieve_node(), which writes the result to
state["rag_context"]. crew_node.py then joins the "fact" fields into a
single string passed to the CrewAI Executor agent, whose task
description instructs it to paraphrase — never quote — these facts
into the itinerary's welcome note (see docs/architecture.md's
copyright-discipline note).

Known gaps (see docs/architecture.md, Limitations):
  - No retry/backoff on request failure. A transient network error or
    non-200 response is indistinguishable from "no matching Wikipedia
    page" — both silently return []. interests.py has retry logic for
    the equivalent Overpass-timeout scenario; this module does not.
  - place_name is passed to Wikipedia's title lookup as-is (spaces
    replaced with underscores only). A request like "Kyoto, Japan"
    becomes the literal title "Kyoto,_Japan", which will NOT match
    Wikipedia's actual page titled "Kyoto" — exact-title matching means
    country-suffixed destination strings (as commonly produced by
    extractor.py) may fail to retrieve any RAG context even when a
    perfectly good Wikipedia article exists. Worth testing which
    destination string shapes actually resolve before relying on
    citation coverage numbers in the eval report.
"""

import requests
from .. import config


def retrieve_destination_context(place_name: str) -> list:
    """
    Fetch a short, grounded background summary for a destination.

    Args:
        place_name: destination name as extracted by extractor.py,
            e.g. "Kyoto, Japan". Passed through to Wikipedia's summary
            endpoint with spaces replaced by underscores — see the
            title-matching caveat in the module docstring.

    Returns:
        A list containing at most one dict:
            {"fact": str, "source_title": str, "source_url": str}
        Returns [] if the page doesn't exist, the request fails
        (non-200 response), or the page has no extract text. These
        three distinct failure modes are not currently distinguished
        by the caller — all look identical (empty list) downstream.
    """
    title = place_name.replace(" ", "_")
    resp = requests.get(
        config.WIKIPEDIA_SUMMARY_URL.format(title=title),
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.HTTP_TIMEOUT_SECONDS,
    )
    if resp.status_code != 200:
        return []

    data = resp.json()
    extract = data.get("extract", "")
    if not extract:
        return []

    return [{
        "fact": extract,
        "source_title": data.get("title", place_name),
        "source_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
    }]