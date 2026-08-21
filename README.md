# Travel Itinerary Planner — Agentic AI Capstone

An agentic travel itinerary planner built with LangGraph (control flow, tool orchestration, guardrails) and CrewAI (multi-agent planning). Given a free-text trip request, it extracts structured trip details, retrieves weather and points-of-interest data in parallel, grounds destination background in Wikipedia via RAG, and produces a day-by-day itinerary through a two-agent Planner→Executor handoff — with deterministic guardrails checking the output before it's released.

Full system design, diagram, and design decisions: [`planner/docs/architecture.md`](planner/docs/architecture.md).
Evaluation methodology and results: [`planner/eval/eval_report.md`](planner/eval/eval_report.md).

---

## Model / Provider

- **Provider:** Anthropic
- **Model:** `claude-sonnet-5`
- **Used in two places:** directly via the `anthropic` Python SDK for structured trip-detail extraction (`planner/orchestrator/extractor.py`), and via CrewAI's `LLM` class for both agents in the Planner→Executor crew (`planner/crewagents/agents.py`). One model, configured once in `planner/config.py`.
- **Why Claude:** chosen for direct, inspectable SDK calls without an additional provider-abstraction layer — see `docs/architecture.md`'s Model/Provider Choice section for the full rationale.
- **Limitations from this choice:**
  - Requires a funded Anthropic API key; the system will not run without one (no local-model fallback is implemented).
  - Subject to Anthropic's rate limits — the eval harness's 13 test cases, each involving multiple LLM calls (1 extraction + at least 2 CrewAI task calls), can take several minutes to run end to end; observed average latency per request in `eval/eval_report.md` is ~35–40 seconds.
  - CrewAI agent output is non-deterministic — the same test case can produce different itinerary text (though similar structure) across runs.
  - No cost tracking is implemented; every run incurs real API cost proportional to test case count and itinerary length.

---

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) with available credit
- [`uv`](https://docs.astral.sh/uv/) (this project uses `uv` for dependency management — `pyproject.toml` + `uv.lock`)

---

## Setup Instructions

1. **Clone the repository** (or download the project files).

2. **Install dependencies** using `uv`:
   ```bash
   uv sync
   ```
   This reads `pyproject.toml`/`uv.lock` and creates a virtual environment with all required packages (`anthropic`, `crewai`, `langgraph`, `mcp`, `requests`, `python-dotenv`, `pytest`).

3. **Set up your API key:**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and replace the placeholder with your real Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-real-key-here
   ```
   `.env` is gitignored and will never be committed — see `.gitignore`.

4. **Verify the install** by running the test suite (see Tests section below).

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key. Loaded via `python-dotenv` from `.env` — see `planner/config.py`. |

No other environment variables are required. All external data sources (Open-Meteo, OpenStreetMap Nominatim/Overpass, Wikipedia REST API) are public and keyless.

---

## Running the Demo

The interactive CLI entry point prompts you for a trip request and runs it through the full pipeline:

```bash
uv run python -m planner.main
```

Example session:
```
Where would you like to go? Describe your trip: Plan a 3-day trip to Kyoto, Japan for $600

Request: Plan a 3-day trip to Kyoto, Japan for $600

=== FINAL ITINERARY ===
...

=== DETAILS ===
Destination: Kyoto, Japan
Trip type:   single_city
Days:        3
Budget:      600.0

=== CITATIONS ===
  - Kyoto: https://en.wikipedia.org/wiki/Kyoto
```

Note that `trip_type` (`single_city`) was inferred automatically from context — a multi-day trip to one destination — without needing to be stated explicitly. `trip_type` is only asked for when nothing in the request gives enough context to infer it, alongside destination and number of days:
```
Where would you like to go? Describe your trip: I want to go to Lisbon

Your request is missing: num_days, trip_type. Please rewrite your request to include this information.
```

Here, "I want to go to Lisbon" gives no day count and no signal about single-city vs. multi-city vs. day-trip — there isn't enough context to infer either field, so the system asks rather than guessing. It is not that `trip_type` must always be typed explicitly (as `single_city`/`multi_city`/`day_trip`) — most requests that state a day count or mention multiple destinations (e.g. "a day trip to X", "visiting X and then Y") will have it inferred silently.

### Known limitation: multi-city requests are not yet supported

The extractor correctly recognizes multi-city intent, but the tool layer (weather/POI lookup) currently expects a single geocodable destination string, so a multi-city request will fail downstream rather than producing an itinerary:

```
Where would you like to go? Describe your trip: Plan a 6-day trip visiting Rome and then Florence, budget $1500

Request: Plan a 6-day trip visiting Rome and then Florence, budget $1500

[an error or empty/blocked result — see docs/architecture.md and eval/eval_report.md's TC10 for the full failure analysis]
```

The extractor correctly infers `trip_type: multi_city` for this request, but `weather_node`/`poi_node` pass the combined string `"Rome and Florence"` to Nominatim/Open-Meteo as if it were one place, which fails to geocode. Per-city tool decomposition (splitting the request into separate weather/POI calls per city, with genuine conditional routing)  is left as an extension for this project — see `docs/architecture.md`'s Limitations for the full explanation, and `eval/eval_report.md`'s TC10 failure analysis for what actually happens when this is run.


## Running Tests

Run the full test suite (13 tests across 5 files):

```bash
uv run python -m pytest planner/tests/ -v
```

Tests that call the Anthropic API (extraction, CrewAI crew) are guarded with `@pytest.mark.skipif` and will skip cleanly if `ANTHROPIC_API_KEY` is not set, rather than failing.

Individual test files:

| File | Covers |
|---|---|
| `planner/tests/extractor_test.py` | Trip-detail extraction, required-field validation, `IncompleteRequestError` |
| `planner/tests/mcp_test.py` | End-to-end MCP client/server round-trip for POI retrieval |
| `planner/tests/wikipedia_rag_test.py` | RAG retrieval and citation fields from the Wikipedia API |
| `planner/tests/crew_test.py` | CrewAI Planner→Executor crew, output structure and Planner→Executor handoff |
| `planner/tests/graph_test.py` | Full LangGraph pipeline, end to end |

Run a single file:
```bash
uv run python -m pytest planner/tests/mcp_test.py -v -s
```

---

## Running the Evaluation

The evaluation harness runs 13 fixed test cases through the full pipeline and reports task success rate, citation coverage, weather-compliance rate, and average latency, including a with/without-weather ablation:

```bash
uv run python -m planner.eval.harness
```

This takes several minutes (each test case involves multiple live API calls). Full methodology, results table, failure analysis, and ablation discussion: [`planner/eval/eval_report.md`](planner/eval/eval_report.md).

---

## Project Structure

```
travel_assistant/
├── .env.example              # placeholder env var names — copy to .env
├── .gitignore
├── pyproject.toml            # dependencies (uv)
├── uv.lock
├── README.md                  # this file
└── planner/
    ├── main.py                 # CLI demo entry point
    ├── config.py                 # central config, loads ANTHROPIC_API_KEY
    ├── orchestrator/               # LangGraph nodes and graph wiring
    │   ├── extractor.py
    │   ├── tool_nodes.py
    │   ├── rag_node.py
    │   ├── crew_node.py
    │   ├── guardrails.py
    │   ├── graph.py
    │   └── planner_state.py
    ├── tools/                        # weather + POI (MCP) tools
    │   ├── weather.py
    │   ├── interests.py
    │   ├── interests_mcp_server.py
    │   └── interest_mcp_client.py
    ├── rag/
    │   └── destination_retriever.py
    ├── crewagents/                     # CrewAI Planner/Executor agents
    │   ├── agents.py
    │   ├── tasks.py
    │   └── crew.py
    ├── tests/                            # 13 tests, see Tests section
    ├── eval/
    │   ├── harness.py
    │   └── eval_report.md
    └── docs/
        └── architecture.md
```

---

## Agentic Patterns Implemented

At least 4 required; this project implements 7 — full detail and code references in [`docs/architecture.md`](planner/docs/architecture.md):

1. **Parallelization** — weather and POI retrieval run concurrently
2. **Tool Use (≥2)** — Open-Meteo (weather), OpenStreetMap (POI)
3. **MCP Integration** — POI retrieval goes through a real MCP server/client pair
4. **Multi-Agent** — CrewAI Planner and Executor agents with an explicit task handoff
5. **RAG** — Wikipedia-grounded destination context with citations
6. **Guardrails** — deterministic output checks before release
7. **Evaluation** — automated harness with 4 metrics and an ablation

---

## AI Assistance Disclosure

This project was developed with substantial assistance from Claude (Anthropic), used throughout the build process as a coding and design assistant. Specific uses included:

- **Architecture planning** — designing the LangGraph/CrewAI split, the node/edge structure, and working through which agentic patterns to implement (and which to deliberately exclude, with justification)
- **Debugging** — diagnosing and resolving real issues encountered during development, including Python package/import structure errors, an MCP client/server tool-name mismatch, a silently-swallowed MCP error-handling gap, `.env` loading order bugs, and dependency version conflicts (e.g. `mcp` package version upgrades)
- **Code generation and review** — writing and reviewing individual modules (tools, LangGraph nodes, CrewAI agents/tasks, guardrails, tests), with the author verifying behavior by running the code and inspecting real output at each step
- **Documentation** — drafting `docs/architecture.md`, `eval/eval_report.md`, and this README, grounded in the actual codebase and real evaluation run data (`eval/raw_run_output.txt`), not hypothetical descriptions
- **Evaluation analysis** — analyzing real `eval/harness.py` output to identify and explain actual failure modes (see `eval/eval_report.md`'s Failure Analysis section)

### All code was run, tested, and reviewed by the author throughout development, not accepted unverified. The author can explain every component, agent, tool, prompt, and design decision in this project, including the specific tradeoffs behind design decisions such as scoping POI search to a single OpenStreetMap category, using MCP for POI retrieval but not weather, and the known, documented gap in `trip_type`'s downstream usage.


## Known Limitations

See [`docs/architecture.md`](planner/docs/architecture.md#limitations) for the full, honest list, including: the RAG retriever's Wikipedia title-matching can miss valid pages for country-suffixed destination strings; POI retrieval is scoped to a single OpenStreetMap category (`park`) as a deliberate latency tradeoff; and `trip_type` is extracted but not yet used to vary planning behavior.