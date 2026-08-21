"""
CrewAI task definitions bound to the Planner and Executor agents.

build_execution_task's context=[planning_task] parameter is the
concrete mechanism of the multi-agent handoff pattern (see
docs/architecture.md) — CrewAI automatically injects planning_task's
finished output into the Executor's prompt before execution_task runs.
Without this line, the Executor would have no knowledge of what
skeleton the Planner actually produced.

Both task descriptions are built via plain Python f-strings — pois,
budget, and weather dicts/lists are interpolated directly via their
repr (e.g. f"...: {pois}"), not serialized through any structured
format (JSON, etc.). This means the LLM receives Python's default
str()/repr() representation of these objects, which is readable but
not a schema-validated format — if pois or weather's shape ever
changes, the prompt's phrasing implicitly depends on what that repr
looks like without any explicit contract enforcing it.

Known mismatch: build_execution_task's prompt instructs the Executor
to avoid "outdoor-tagged activities (parks, viewpoints)" on high-rain
days, but tools/interests.py is currently scoped to the "park" category
only (see that module's docstring re: the deliberate latency tradeoff)
— "viewpoints" can never actually appear in pois under the current
scoping, making that part of the instruction dead weight. Worth
updating this wording to match the current single-category scope, or
reconsidering the scoping decision if viewpoint-avoidance matters.

The weather-compliance instruction here (lines re: precipitation >50%)
is the generative counterpart to guardrails.py's weather-compliance
CHECK — the task tells the Executor what to do, guardrails.py verifies
after the fact whether it happened (via a crude "does the text mention
rain/weather" keyword check, not true schedule verification — see that
module's docstring for the distinction).

The RAG-citation instruction ("paraphrasing (never quoting)") is the
project's only explicit copyright-discipline instruction anywhere in
the codebase — worth keeping in mind if rag_facts is ever expanded to
include longer or multiple Wikipedia extracts, since longer source
text increases the risk of the LLM drifting toward closer paraphrase
or partial quotation despite the instruction.
"""
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