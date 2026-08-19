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