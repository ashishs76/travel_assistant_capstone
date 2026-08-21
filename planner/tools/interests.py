"""
Tool: points of interest (POIs).

Data source: OpenStreetMap — free, public, no API key.
  - Nominatim geocodes the destination name into a bounding box.
  - Overpass queries tourism/leisure-tagged POIs within that box.

This module is called directly by tests and can also be invoked as a
script (see __main__ below). In the production pipeline it's wrapped
by interests_mcp_server.py so retrieval goes over MCP rather than a
direct import — see docs/architecture.md, Design Decision #2, for why
MCP wraps POI specifically and not the weather tool.
"""

import requests
import time
from .. import config

# Scoped to "park" only (not the full museum/attraction/restaurant/park)
# as a deliberate tradeoff: fewer Overpass tag
# filters per query reduces response payload size and latency, at the
# cost of itinerary variety. See docs/architecture.md, Design Decision
# #3, for the full justification. Unrecognized category names passed
# to search_pois() are silently ignored rather than raising an error.

CATEGORY_TAGS = {
    "park": "leisure=park",
}

def _geocode_bbox(place_name: str) -> list:
    """
    Resolve a place name to a bounding box via Nominatim.

    Returns [south, north, west, east] as floats, matching Nominatim's
    boundingbox response order.

    Raises:
        ValueError: if Nominatim returns no results for place_name.
        requests.exceptions.HTTPError: if the Nominatim request itself fails
            (not retried — geocoding failures are treated as non-transient).
    """
    resp = requests.get(
        config.NOMINATIM_URL,
        params={"q": place_name, "format": "json", "limit": 1},
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"Could not geocode '{place_name}' via Nominatim")
    return [float(x) for x in results[0]["boundingbox"]]

def search_pois(place_name: str, categories: list = None, limit: int = 20, max_retries: int = 3) -> list:
    """
        Search OpenStreetMap (via the public Overpass API) for points of
        interest near a place.

        Args:
            place_name: destination name, e.g. "Kyoto, Japan". Geocoded via
                Nominatim to determine the search bounding box.
            categories: subset of CATEGORY_TAGS keys to search for (e.g.
                ["park"]). Unrecognized category names are silently ignored.
                Defaults to all keys in CATEGORY_TAGS if not provided.
            limit: maximum number of POIs to return.
            max_retries: number of attempts before giving up on a 5xx error
                from Overpass, with exponential backoff (1s, 2s, 4s, ...)
                between attempts. Overpass's public instance is free and
                unauthenticated, and intermittently returns 504 Gateway
                Timeout under load — this retry logic is the mitigation
                (see docs/architecture.md, Limitations).

        Returns:
            A list of dicts, one per POI, each with:
                name, lat, lon, opening_hours (may be None), source.
            POIs without a "name" tag in OSM are skipped — an unnamed node
            isn't useful to show a traveler.

        Raises:
            ValueError: if place_name can't be geocoded (propagated from
                _geocode_bbox, not retried).
            requests.exceptions.HTTPError: if all max_retries attempts
                against Overpass fail.
        """
    categories = categories or list(CATEGORY_TAGS.keys())
    south, north, west, east = _geocode_bbox(place_name)
    tag_filters = "".join(
        f"node[{CATEGORY_TAGS[c]}]({south},{west},{north},{east});"
        for c in categories if c in CATEGORY_TAGS
    )
    query = f"[out:json][timeout:40];( {tag_filters} );out center {limit};"

    resp = None
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                config.OVERPASS_URL, data={"data": query},
                headers={"User-Agent": config.USER_AGENT}, timeout=45,
            )
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    else:
        raise last_error

    elements = resp.json().get("elements", [])
    pois = []
    for el in elements[:limit]:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        pois.append({
            "name": name, "lat": el.get("lat"), "lon": el.get("lon"),
            "opening_hours": tags.get("opening_hours"), "source": "openstreetmap.org",
        })
    return pois

if __name__ == "__main__":
    # Quick manual smoke test — run directly with:
    #   python -m planner.tools.interests
    print(search_pois("Florida, USA",limit=3))