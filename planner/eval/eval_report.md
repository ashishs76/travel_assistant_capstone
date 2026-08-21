# Evaluation Report — Travel Itinerary Planner

## Methodology
13 test cases run against the full LangGraph pipeline (extractor → weather/POI
parallel → RAG → CrewAI crew → guardrails). Cases cover: complete well-formed
requests (8), an edge-case destination (1), deliberately incomplete requests
to test the human-in-the-loop rejection path (2), and an unresolvable
destination to test tool-failure handling (1). All cases in eval/../TEST_CASES.

## Metrics
- **Task success rate** — itinerary produced with zero guardrail violations
- **Citation coverage** — % of runs where RAG context was retrieved
- **Weather compliance rate** — for high-rain-probability trips, % where the
  itinerary text acknowledges a weather-based adjustment
- **Avg latency** — end-to-end wall clock per request

## Results
SUMMARY (full system):
  task_success_rate: 0.69
  citation_coverage: 0.69
  weather_compliance_rate: 1.0
  avg_latency_sec: 39.43
  total_cases: 13

Test runs:
[           success] TC01: Plan a 3-day trip to Kyoto, Japan for $600, single city  (45.94s)

[           success] TC02: Plan a 5-day trip to Lisbon, Portugal for $1000, single city  (45.36s)
[           success] TC03: Plan a 2-day trip to Cancun, Mexico for $400, single city  (34.61s)
[           success] TC04: Plan a 4-day trip to Rome, Italy for $800, single city  (40.95s)
[           success] TC05: Plan a day trip to Central Park, New York  (29.9s)
[           success] TC06: Plan a 3-day trip to Bangkok, Thailand for $300, single city  (80.69s)
[           success] TC07: Plan a 6-day trip to Barcelona, Spain for $1200, single city  (55.5s)
[           success] TC08: Plan a 2-day trip to Reykjavik, Iceland for $500, single cit  (37.0s)
[           success] TC09: Plan a 3-day trip to Marrakech, Morocco for $450, single cit  (53.55s)
[ guardrail_blocked] TC10: Plan a 6-day trip visiting Rome and then Florence, budget $1  (53.42s)
[incomplete_request] TC11: I want to go to Lisbon  (2.23s)
[incomplete_request] TC12: Plan a trip for $500  (2.74s)
[ guardrail_blocked] TC13: Plan a 3-day trip to Xyzzyplonkistan for $500, single city  (30.64s)

=== ABLATION: NO WEATHER ===
SUMMARY (no weather ablation):
  task_success_rate: 0.69
  citation_coverage: 0.69
  weather_compliance_rate: N/A
  avg_latency_sec: 37.64
  total_cases: 13

Test runs:
[           success] TC01: Plan a 3-day trip to Kyoto, Japan for $600, single city  (55.09s)

[           success] TC02: Plan a 5-day trip to Lisbon, Portugal for $1000, single city  (53.14s)
[           success] TC03: Plan a 2-day trip to Cancun, Mexico for $400, single city  (38.08s)
[           success] TC04: Plan a 4-day trip to Rome, Italy for $800, single city  (55.81s)
[           success] TC05: Plan a day trip to Central Park, New York  (27.03s)
[           success] TC06: Plan a 3-day trip to Bangkok, Thailand for $300, single city  (54.27s)
[           success] TC07: Plan a 6-day trip to Barcelona, Spain for $1200, single city  (47.71s)
[           success] TC08: Plan a 2-day trip to Reykjavik, Iceland for $500, single cit  (32.73s)
[           success] TC09: Plan a 3-day trip to Marrakech, Morocco for $450, single cit  (43.06s)
[ guardrail_blocked] TC10: Plan a 6-day trip visiting Rome and then Florence, budget $1  (41.08s)
[incomplete_request] TC11: I want to go to Lisbon  (1.6s)
[incomplete_request] TC12: Plan a trip for $500  (2.58s)
[ guardrail_blocked] TC13: Plan a 3-day trip to Xyzzyplonkistan for $500, single city  (37.16s)