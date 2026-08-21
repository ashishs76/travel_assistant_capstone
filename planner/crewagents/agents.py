"""
CrewAI agent definitions: Planner and Executor.

This is the multi-agent half of the project's Design Decision #1 split
(LangGraph owns infrastructure/control-flow, CrewAI owns agent
collaboration — see docs/architecture.md). Both agents share a single
LLM instance (Claude, configured once from config.py) rather than each
constructing their own — this guarantees model/key consistency across
the crew and avoids re-instantiating the client per agent.

verbose=True on both agents is intentional, not leftover debug code:
it prints each agent's reasoning/tool-use trace to stdout, which is
useful for the recorded demo (shows the Planner->Executor handoff
happening live) but will be noisy when running the eval harness across
many test cases — consider whether to suppress it for eval runs vs.
keep it for the demo recording specifically.

Note: the Planner agent's goal text mentions "respecting ... the
traveler's preferences," but no distinct "preferences" field is
currently threaded through from extractor.py -> crew_node.py -> here;
only destination, num_days, budget, pois, weather, and rag_facts are
actually passed as task inputs (see crewagents/tasks.py). The goal
text may be slightly aspirational relative to what data the agent
actually receives — worth tightening the wording or actually adding a
preferences field if this matters for your demo.

These functions are called fresh on every crew_node() invocation (see
crewagents/crew.py's run_travel_crew()) rather than being module-level
singletons — a new Agent object is built per request. This is
consistent with treating each planning request as fully independent
(no cross-request memory — see docs/architecture.md's "memory
deliberately excluded" justification).
"""
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