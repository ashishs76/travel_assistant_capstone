from crewai import Task

def build_planning_task(agent, destination, num_days, pois, budget):
    return Task(
        description=(
            f"Create a day-by-day skeleton for a {num_days}-day trip to {destination}. "
            f"Available points of interest: {pois}. Budget: {budget}. "
            f"Distribute activities across days, no more than 5 per day."
        ),
        expected_output="A day-by-day list of which activities go on which day.",
        agent=agent,
    )


def build_execution_task(agent, planning_task, weather, rag_facts):
    return Task(
        description=(
            f"Using the day-by-day skeleton from the previous step, add an estimated cost "
            f"and short note per activity. Weather context: {weather}. "
            f"IMPORTANT: if a day's precipitation probability exceeds 50%, avoid scheduling "
            f"outdoor-tagged activities (parks, viewpoints) that day — prefer museums, "
            f"restaurants, and other indoor options, and note in that day's summary that "
            f"the schedule was adjusted for rain. "
            f"Write a 1-2 sentence welcome note paraphrasing (never quoting) these facts: {rag_facts}."
        ),
        expected_output="A finalized itinerary with per-day cost estimates and a welcome note.",
        agent=agent,
        context=[planning_task],   # <- this is the explicit handoff
    )