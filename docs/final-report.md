# Workplace Compliance Advisory Desk — project report

## Problem and scope

HR statutory questions can depend on amendments, commencement dates, repeals and provisos. The service validates a synthetic question, retrieves exact passages, verifies provenance/status and either returns a cited information result or escalates. It never gives a legal opinion. No personal employee data is permitted.

## Agent design

Research and verification responsibilities run as separate Python agents connected by LangGraph. Graph nodes classify, check missing facts, apply human-review gates, research, verify, retry once with a derived search and decide. The research agent has a four-call and five-second budget per execution; the graph retries no more than once. Each workflow node, tool query, retrieved passage and verification result is persisted after execution. Production requests use Redis/Celery; local requests use a thread. Separate agent services, incremental node persistence during crashes and provider-based answer generation remain incomplete.

## Architecture and deployment boundaries

The intended boundaries are React UI, FastAPI gateway, Celery worker, PostgreSQL, Redis, optional Chroma, Prometheus/Grafana and Jaeger. Worker replicas isolate long-running work. API request metrics, durable run/decision/agent gauges, cache counters and a provisioned Grafana dashboard are present. Application OpenTelemetry export and per-container resource metrics remain incomplete. Compose syntax validates, but Docker Desktop's Linux engine pipe was unavailable for live startup verification.

## Decisions and rejected alternatives

- Chose exact-text lexical fallback and fail-closed routing while primary Act PDFs are unavailable; fabricated statute text or citations were rejected.
- Chose background execution to keep the HTTP request short.
- Chose no real employee records and hash-only invalid-request quarantine to limit sensitive data retention.
- Semantic vector retrieval, provider synthesis and a full UI page set are deferred until the source corpus and runtime environment are validated.

## Evaluation

Twenty synthetic scenarios are runnable. Current report records 19/20 outcome decisions (0.95), escalation correctness 1.0, clarification correctness 1.0, retrieval precision/recall 0.0 on the labeled difficult case, and lexical context relevance 0.170955. There are zero generated answers, so groundedness, faithfulness, citation quality and hallucination rate are not measurable. Prompt versions are not compared because generation is not in the workflow. The fixed-term expected scenario is included and fails safely to counsel review; it is not passed.

## Performance and cost

Predeclared SLO: complete asynchronous run p95 under 30 seconds at 20 concurrent synthetic clients with the fixed-delay stub, based on the assignment's “tens of seconds” run duration. A local stub-backed 20-user/30-second Locust run completed 209 full runs with no failures; complete-run p50/p95/p99 were 1.7/2.6/2.8 seconds. It met the 30-second p95 target in this local single-process setup. Docker deployment, worker scaling, resource use, provider tokens and cost per 100 runs remain unmeasured; no pricing is invented. See `performance-report.md` and the raw `performance-20users_*.csv` files.

## What did not work / limitations

India Code PDF requests timed out and an alternate Ministry URL returned 404. Three official guidance/notification documents are indexed, but the primary Code on Social Security and POSH Act texts are missing; the local workflow therefore escalates the difficult fixed-term gratuity scenario instead of asserting an answer. Chroma indexing is optional and has not been run against a live Chroma endpoint. Independent agent deployment, Alembic migrations, container resource metrics, application OTel spans, output toxicity checks, model-backed answers and cost attribution remain unfinished. Docker startup and Locust scaling require a reachable Docker Engine.

See `DEVELOPMENT_PROGRESS.md`, `docs/requirements-traceability.md`, `docs/runbook.md` and `docs/incident-log.md` for verification and operational detail.
# Acceptance update (2026-10-28)

The earlier summary below predates successful Compose startup. Current live state and evidence: Compose is running, API/PostgreSQL/Redis are healthy, Celery worker is ready, Alembic additive revision `0001_additive_baseline` is applied, and a live async job persisted agent traces. A narrow Section 53 commencement query returns a citation to the local Gazette notification. Primary statutory PDFs remain missing, so the fixed-term gratuity case escalates. Current tests: 36 passed, including ten source/fixed-term regressions; frontend Vite build passed; deterministic 20-case evaluation has 0.95 outcome accuracy with no answer-quality metrics measured. The canonical updated status is in [`FINAL_ACCEPTANCE_REPORT.md`](FINAL_ACCEPTANCE_REPORT.md).
