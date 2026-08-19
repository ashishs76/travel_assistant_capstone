"""
RAG retriever — grounds destination background in Wikipedia, with citations.

Data source: Wikipedia REST API (public, keyless).
"""

import requests
from .. import config


def retrieve_destination_context(place_name: str) -> list:
    """
    Returns a list of {"fact": str, "source_title": str, "source_url": str}.
    Empty list if no matching Wikipedia page is found.
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