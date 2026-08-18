import requests
import time
from .. import config

CATEGORY_TAGS = {
    "park": "leisure=park",
}

def _geocode_bbox(place_name: str) -> list:
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
    print(search_pois("Cancun, Mexico",limit=3))