flowchart TD
    U["User Request<br/>(e.g. '5-day Japan trip, vegetarian, $2000')"] --> R

    subgraph CTRL["LangGraph — Control Flow (Router & Parallel Fan-out)"]
        R{{"Router Node<br/>classify: single-city /<br/>multi-city / day-trip"}}
        R -->|parallel| W["Weather Tool Node<br/>(Open-Meteo API, direct call)"]
        R -->|parallel| P["POI Tool Node<br/>(OSM via MCP Server)"]
        W --> M["Merge Node"]
        P --> M
    end

    M --> RAG

    subgraph RAGB["LangGraph — RAG"]
        RAG["Retriever Node<br/>Wikipedia REST API"] --> RAGC["Cited Context<br/>(facts + source URL)"]
    end

    RAGC --> CREW

    subgraph CREWB["crew_node (single LangGraph node)"]
        direction TB
        CNOTE["LangGraph hands off state to CrewAI here —<br/>everything below is internal to crew.kickoff()"]
        PLANNER["CrewAI Agent: Planner<br/>produces day-by-day skeleton"]
        EXECUTOR["CrewAI Agent: Executor<br/>fills in cost/duration/notes<br/>per day"]
        PLANNER -->|explicit task handoff| EXECUTOR
        CNOTE -.-> PLANNER
    end

    CREW["crew_node"] -.->|wraps| CREWB
    CREWB --> GR

    subgraph GUARD["LangGraph — Guardrails & Eval"]
        GR["Guardrail Check<br/>budget ceiling, max activities/day"]
        EVAL["Eval Harness<br/>(offline, ≥10 test cases)"]
    end

    GR --> OUT["Final Itinerary<br/>+ citations"]
    EVAL -.->|offline testing, not in live request path| CTRL
    EVAL -.-> CREWB

    style CTRL fill:#e8f0fe,stroke:#4285f4
    style RAGB fill:#fef7e0,stroke:#f9ab00
    style CREWB fill:#e6f4ea,stroke:#34a853
    style GUARD fill:#f3e8fd,stroke:#a142f4