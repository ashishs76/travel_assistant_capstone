from crewai import Agent, LLM
from .. import config

claude = LLM(model=f"anthropic/{config.ANTHROPIC_MODEL}", api_key=config.ANTHROPIC_API_KEY)

def build_planner_agent() -> Agent:
    return Agent(
        role="Trip Planner",
        goal="Distribute available points of interest across the requested number of days, "
             "respecting the traveler's budget and preferences.",
        backstory="An experienced travel planner who organizes rough day-by-day skeletons "
                   "before details are filled in.",
        llm=claude,
        verbose=True,
    )


def build_executor_agent() -> Agent:
    return Agent(
        role="Itinerary Executor",
        goal="Take a day-by-day skeleton and add estimated costs, timing, and a short "
             "grounded welcome note for the traveler.",
        backstory="A detail-oriented local guide who fleshes out plans with practical specifics.",
        llm=claude,
        verbose=True,
    )