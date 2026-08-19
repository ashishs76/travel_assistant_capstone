from dotenv import load_dotenv
load_dotenv()

from planner.crewagents.crew import run_travel_crew

sample_pois = [
    {"name": "Chichen Itza", "category": "attraction"},
    {"name": "Playa Delfines", "category": "attraction"},
    {"name": "La Habichuela Sunset", "category": "restaurant"},
]
sample_weather = {"days": [{"date": "2026-09-01", "temp_max_c": 32, "precip_probability_pct": 40}]}
sample_rag = "Cancun developed rapidly after Mexico's government identified it as a prime location for tourism in the 1970s, and it is now known for its beaches along the Caribbean coast and nearby Maya archaeological sites."

result = run_travel_crew(
    destination="Cancun, Mexico",
    num_days=2,
    pois=sample_pois,
    budget={"total_ceiling_usd": 400, "per_day_ceiling_usd": 200},
    weather=sample_weather,
    rag_facts=sample_rag,
)
print(result.raw)