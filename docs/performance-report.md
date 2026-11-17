# Performance Report

## Latest local stub profile

On 2026-11-16, Locust 2.47.0 exercised the local FastAPI workflow for 30 seconds with 20 users and a spawn rate of 20 users/second. The profile used `LLM_PROVIDER=stub`, disabled LangSmith tracing, used a 1.2-second fixed response, increased the test-only API rate limit, and wrote to a separate SQLite database at `tmp/runtime-perf-2026-11-16.sqlite`. No Gemini calls or test runs against the main local database were part of this load test.

| Measure | Result |
|---|---:|
| HTTP requests / reported failures | 1,321 / 0 |
| Submissions | 122; p50/p95 0.34/1.70 seconds |
| Complete-run measurements | 107; p50/p95 3.70/6.40 seconds |
| Poll requests | 1,092; p50/p95 0.11/0.65 seconds |
| Aggregated HTTP p50/p95 | 0.14/3.50 seconds |
| In-flight difference at shutdown | 15 submissions not included as completed-run measurements |

Raw outputs: `performance-live-stub-2026-11-16_stats.csv`, `performance-live-stub-2026-11-16_stats_history.csv`, `performance-live-stub-2026-11-16_failures.csv`, and `performance-live-stub-2026-11-16_exceptions.csv`.

This is a local single-process SQLite/stub profile. It does not establish Gemini, Docker, multiworker, or production capacity. The live Gemini probe timed out, and Docker services were unavailable.

## Historical local profile

The 2026-10-28 historical run used 20 Locust users and a stub-backed local API with SQLite. It recorded 209 complete runs, zero reported failures, and complete-run p50/p95/p99 of 1.7/2.6/2.8 seconds. Its CSV files retain the `performance-20users_*` names. Keep these measurements separate from the 2026-11-16 run because the software and request timings differ.

## Evaluation context

The latest deterministic evaluation uses 30 cases: outcome accuracy 29/30, classification accuracy 21/28, escalation correctness 1.0, clarification correctness 1.0, retrieval precision/recall 0.0 on labeled statutory passages, and answer-run denominator zero. It measures safety routing and retrieval, not generated-answer quality. See [`evaluation-results.json`](evaluation-results.json).
