"""
Assembles the Planner and Executor agents plus their tasks into a
CrewAI Crew and runs it. This is the function crew_node.py calls —
everything in this file (and everything it calls into: agents.py,
tasks.py) is invisible to LangGraph, which only sees crew_node as a
single node. See docs/architecture.md, Design Decision #1, for the
LangGraph/CrewAI ownership split this function sits at the center of.

Process.sequential means the crew runs planning_task fully to
completion, then execution_task — this is what makes the
context=[planning_task] handoff in tasks.py meaningful: by the time
execution_task runs, planning_task's output already exists and is
injected into the Executor agent's prompt. (CrewAI also supports
Process.hierarchical, with a manager agent delegating — not used here;
sequential was chosen since the task shape is fixed and known upfront,
consistent with the project's decision not to implement a
planning/ReAct pattern on top of this — ordering doesn't need to be
decided dynamically.)

Both agents and both tasks are constructed fresh on every call — see
agents.py's docstring re: no cross-request state or singleton reuse.

verbose=True here (Crew-level) is separate from verbose=True set on
each individual Agent in agents.py — both contribute to the console
output during a run; see agents.py's docstring re: this being noisy
across the eval harness's 13 test cases.

Known gap: no error handling. If either task's underlying LLM call
fails, or CrewAI itself raises internally, this propagates unhandled
up through crew_node.py (which also has no error handling — see that
module's docstring, Known gap) and crashes the graph. This is the
single point in the pipeline where the most LLM round-trips happen
(at least two: one per task, potentially more depending on CrewAI's
internal retry/tool-use behavior), making it statistically the most
likely failure point with currently the least failure handling.
"""
from crewai import Crew, Process
from .agents import build_planner_agent, build_executor_agent
from .tasks import build_planning_task, build_execution_task


def run_travel_crew(destination, num_days, pois, budget, weather, rag_facts):
    planner_agent = build_planner_agent()
    executor_agent = build_executor_agent()

    planning_task = build_planning_task(planner_agent, destination, num_days, pois, budget)
    execution_task = build_execution_task(executor_agent, planning_task, weather, rag_facts)

    crew = Crew(
        agents=[planner_agent, executor_agent],
        tasks=[planning_task, execution_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew.kickoff()