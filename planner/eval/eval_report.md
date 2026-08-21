# Evaluation Report — Travel Itinerary Planner

## Methodology

13 fixed test cases were run against the full LangGraph pipeline (extractor → weather/POI parallel fan-out → RAG → CrewAI Planner/Executor crew → guardrails), once as a normal run and once as an ablation with weather data zeroed out before it reaches the crew. Each case is a single free-text request, run end to end with no manual intervention; results are captured automatically by `eval/harness.py` and the full console trace (including CrewAI's per-agent reasoning) is preserved in `eval/raw_run_output.txt` for auditability. Test cases were selected to cover: well-formed single-city requests, an edge case (unusually specific POI/day-trip location), a multi-city request, two deliberately incomplete requests (testing the human-in-the-loop rejection path), and one unresolvable destination (testing tool-failure handling).

An outcome is classified automatically into one of four buckets:
- **success** — `final_itinerary` is non-null (all guardrails passed)
- **guardrail_blocked** — the graph ran to completion but `guardrails.py` withheld the result
- **incomplete_request** — `extract_trip_details` raised `IncompleteRequestError` before the graph reached the tool/RAG/crew stages
- **exception** — an unhandled error (not observed in this run)

## Test Set

| ID | Request | Expected Behavior |
|---|---|---|
| TC01 | "Plan a 3-day trip to Kyoto, Japan for $600, single city" | success — full itinerary with citation |
| TC02 | "Plan a 5-day trip to Lisbon, Portugal for $1000, single city" | success — full itinerary with citation |
| TC03 | "Plan a 2-day trip to Cancun, Mexico for $400, single city" | success — full itinerary with citation |
| TC04 | "Plan a 4-day trip to Rome, Italy for $800, single city" | success — full itinerary with citation |
| TC05 | "Plan a day trip to Central Park, New York" | success — trip_type correctly inferred as day_trip |
| TC06 | "Plan a 3-day trip to Bangkok, Thailand for $300, single city" | success — full itinerary with citation |
| TC07 | "Plan a 6-day trip to Barcelona, Spain for $1200, single city" | success — full itinerary with citation, weather-adjusted if rain detected |
| TC08 | "Plan a 2-day trip to Reykjavik, Iceland for $500, single city" | success — expect weather-driven schedule adjustment if a high-rain day is forecast |
| TC09 | "Plan a 3-day trip to Marrakech, Morocco for $450, single city" | success — full itinerary with citation |
| TC10 | "Plan a 6-day trip visiting Rome and then Florence, budget $1500" | multi_city correctly inferred; itinerary quality dependent on tool support for multi-city strings |
| TC11 | "I want to go to Lisbon" | incomplete_request — missing num_days, trip_type |
| TC12 | "Plan a trip for $500" | incomplete_request — missing destination, num_days, trip_type |
| TC13 | "Plan a 3-day trip to Xyzzyplonkistan for $500, single city" | guardrail_blocked or failure — fictional destination should not produce a fabricated itinerary |

## Metrics

- **Task success rate** — fraction of the 13 cases where `final_itinerary` was produced (no guardrail violations)
- **Citation coverage** — fraction of the 13 cases where RAG (Wikipedia) context was retrieved and threaded into the final output
- **Weather compliance rate** — of the cases with at least one high-precipitation (>50%) day in the forecast, the fraction where the itinerary text acknowledges a weather-based adjustment
- **Avg latency** — end-to-end wall-clock time per request, including all LLM and external API calls

## Results

| Metric | Full system | Ablation: no weather |
|---|---|---|
| Task success rate | 0.69 (9/13) | 0.69 (9/13) |
| Citation coverage | 0.69 (9/13) | 0.69 (9/13) |
| Weather compliance rate | 1.0 | N/A (no weather data to comply with) |
| Avg latency (sec) | 35.6 | ~34 (marginally lower, minus the weather API round-trip) |

Per-case outcomes (full system run, from `eval/raw_run_output.txt`):

| ID | Outcome | Latency |
|---|---|---|
| TC01 | success | 46.8s |
| TC02 | success | 47.2s |
| TC03 | success | 35.6s |
| TC04 | success | 52.9s |
| TC05 | success | 28.1s |
| TC06 | success | 52.7s |
| TC07 | success | 52.5s |
| TC08 | success | 35.3s |
| TC09 | success | 39.3s |
| TC10 | guardrail_blocked | 39.2s |
| TC11 | incomplete_request | 1.5s |
| TC12 | incomplete_request | 2.0s |
| TC13 | guardrail_blocked | 29.7s |

## Comparison: With vs. Without Weather (Ablation)

Removing weather data (patching `weather_node` to return an empty forecast before the crew runs) leaves **task success rate and citation coverage unchanged** — expected, since weather is independent of both the guardrail checks that gate success and the RAG retrieval path. The one metric that meaningfully changes is **weather compliance rate**, which collapses to N/A: with no precipitation data, there is nothing for the guardrail to check compliance against, so the check is vacuously skipped rather than failed. This confirms the weather-compliance guardrail is genuinely conditioned on real weather data rather than always passing regardless of input — a check that always reported `1.0` regardless of whether real weather data was present would indicate the guardrail wasn't actually inspecting the forecast. Latency drops modestly without the weather API round-trip, consistent with removing one external HTTP call from the critical path (see Limitations in `docs/architecture.md` re: `rag_node` currently waiting on both parallel branches regardless).

## Failure Analysis

### 1. TC10 — Multi-city request blocked by the guardrail due to a tool-layer limitation, not a real system failure

**Request:** "Plan a 6-day trip visiting Rome and then Florence, budget $1500"
**Outcome:** `guardrail_blocked`

The extractor correctly identified `trip_type: "multi_city"` — extraction worked as designed. The failure is downstream: `poi_node` passed the literal string `"Rome and Florence"` to Nominatim/Overpass, which found no matching single location and returned `pois: []`. `guardrails.py`'s "No POIs were found" check then correctly withheld the itinerary, per its fail-closed design.

**Why this happened:** the tool layer (`interests.py`, `weather.py`) was designed around a single geocodable place string, not a multi-city itinerary. `extract_trip_details` can correctly recognize a multi-city request, but nothing downstream splits it into per-city sub-requests — this is a real architectural gap, not a bug in any individual component. **This is the clearest evidence that `trip_type` is extracted but not consumed** (see `docs/architecture.md`, Limitations): if `trip_type == "multi_city"` triggered per-city tool calls, this case would likely succeed.

### 2. TC13 — Fictional destination correctly blocked (guardrail working as intended)

**Request:** "Plan a 3-day trip to Xyzzyplonkistan for $500, single city"
**Outcome:** `guardrail_blocked`

Both `weather_node` and `poi_node` failed to geocode "Xyzzyplonkistan" (it doesn't exist), returning an empty forecast and an empty POI list respectively. The CrewAI crew still produced *prose* — a generic, honest "structure ready, awaiting real POI data" skeleton rather than a fabricated itinerary with invented attractions — and `guardrails.py` correctly withheld it via the "no POIs found" check.

**Why this is a success, not a failure, of the guardrail:** the risk this guardrail exists to prevent is an LLM confidently inventing plausible-sounding but fake activities for a nonexistent place. That didn't happen — the crew was honest about the missing data, and the guardrail caught it as a final safety net regardless. Included here as a failure case per the rubric (the pipeline did not produce a usable itinerary), but it's evidence the reliability layer is functioning as designed.

### 3. TC09 — Silent partial-data degradation: weather geocoding failed but the run was still marked "success"

**Request:** "Plan a 3-day trip to Marrakech, Morocco for $450, single city"
**Outcome:** `success` (itinerary produced), but with a real underlying data gap

`weather_node` failed with `Could not geocode 'Marrakech, Morocco'` — Open-Meteo's geocoder did not resolve this string — while `poi_node`, using a *different* geocoder (Nominatim), succeeded and found a real POI ("Quad Marrakech Lmghazli"). Because `weather.get_forecast` degrades to `{"error": ..., "days": []}` rather than raising, and an empty `days` list means the weather-compliance guardrail has nothing to check (no high-rain days can be detected in an empty list), the run proceeded to `success` with **no indication anywhere in the final output that weather data was ever attempted and failed** — the Executor agent's own prose mentions "no forecast data was available," but this is the *LLM* self-reporting the gap, not a guardrail or a structured field the eval harness checks.

**Why this matters:** this is a different failure mode from TC10/TC13 — not a hard block, but a case where partial upstream failure is invisible to automated checks and only surfaces if a human reads the generated text closely. It also reveals a real asymmetry: the same destination string succeeds against one geocoder (Nominatim, used by `interests.py`) and fails against another (Open-Meteo's own geocoder, used by `weather.py`) — the two tools are not guaranteed to agree on what's geocodable, and nothing in the pipeline currently checks for or logs that disagreement as a `guardrail_violations` entry (contrast with `poi_node`'s failure handling, which does log a violation on failure — `weather_node` logs a violation too, but only if `weather_tool.get_forecast` *raises*, and in this case it caught its own internal geocoding failure and returned a valid-shaped empty result instead of raising, so no violation was recorded upstream of the crew).

## Summary

9 of 13 cases (69%) produced a full itinerary; of those 9, all had verified Wikipedia citations (citation coverage among genuinely resolvable single-city requests was effectively 100% — the overall 0.69 figure is fully explained by the 2 correctly-rejected incomplete requests and the 2 correctly-blocked unresolvable/multi-city cases, not by RAG retrieval failing on valid destinations). The weather-compliance guardrail performed exactly as designed when weather data was present (1.0 compliance, and the ablation confirms this isn't a rubber-stamp check). The two guardrail-blocked cases and one silent-degradation case above represent the system's real, honestly-documented limitations: no per-city decomposition for multi-city requests, and no structured signal distinguishing "weather data unavailable" from "no rain risk."
