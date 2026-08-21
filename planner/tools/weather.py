"""
Tool: weather forecast.

Data source: Open-Meteo (https://open-meteo.com) — free, public, no
API key required. Two-step call: geocode the destination name to
coordinates, then fetch the daily forecast for those coordinates.

Called directly (not via MCP) — chosen over wrapping it in MCP since
it's a single stateless call with no need for a swappable-provider
boundary; see docs/architecture.md, Design Decision #2, for the full
comparison against interests.py (which IS wrapped in MCP).

Note: unlike interests.py, this module has no retry/backoff logic — a
transient Open-Meteo failure will raise requests.exceptions.HTTPError
directly. This is an acceptable asymmetry since Open-Meteo has proven
more reliable than the public Overpass instance during development,
but the resilience at the pipeline level currently comes entirely from
tool_nodes.weather_node()'s try/except, not from this module itself.
"""
import requests
from .. import config

def geocode(place_name: str) -> dict:
    """
    Resolve a place name to coordinates via Open-Meteo's geocoding API.

    Args:
        place_name: destination name, e.g. "Kyoto, Japan".

    Returns:
        A dict with name, lat, lon.

    Raises:
        ValueError: if no matching location is found.
        requests.exceptions.HTTPError: if the request itself fails
            (not retried — see module docstring).
    """
    resp = requests.get(
        config.OPEN_METEO_GEOCODE_URL,
        params={"name": place_name, "count": 1},
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise ValueError(f"Could not geocode '{place_name}'")
    top = results[0]
    return {"name": top["name"], "lat": top["latitude"], "lon": top["longitude"]}


def get_forecast(place_name: str, num_days: int = 5) -> dict:
    """
    Fetch a daily weather forecast for a destination.

    Args:
        place_name: destination name, e.g. "Kyoto, Japan". Geocoded
            internally via geocode() before the forecast call.
        num_days: number of forecast days requested. Clamped to
            Open-Meteo's supported range of 1-16 days; values outside
            that range are silently clamped rather than raising.

    Returns:
        A dict with:
            location: the geocoded {name, lat, lon}
            days: a list of per-day dicts (date, temp_max_c, temp_min_c,
                  precip_probability_pct) — this is what guardrails.py's
                  weather-compliance check and the CrewAI Executor agent
                  both read.
            source: "open-meteo.com", for provenance.

    Raises:
        ValueError: propagated from geocode() if the place can't be found.
        requests.exceptions.HTTPError: if the forecast request fails
            (not retried — see module docstring).
    """
    loc = geocode(place_name)
    resp = requests.get(
        config.OPEN_METEO_FORECAST_URL,
        params={
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": min(max(num_days, 1), 16),
            "timezone": "auto",
        },
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.HTTP_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    days = [
        {
            "date": date,
            "temp_max_c": daily.get("temperature_2m_max", [None])[i],
            "temp_min_c": daily.get("temperature_2m_min", [None])[i],
            "precip_probability_pct": daily.get("precipitation_probability_max", [None])[i],
        }
        for i, date in enumerate(daily.get("time", []))
    ]
    return {"location": loc, "days": days, "source": "open-meteo.com"}

if __name__ == "__main__":
    print(get_forecast("Cancun, Mexico", 3))