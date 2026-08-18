import requests
from .. import config

def geocode(place_name: str) -> dict:
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