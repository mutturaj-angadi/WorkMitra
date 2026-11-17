# Requirements traceability

The five-page assignment PDF defines the F/A/L/D identifiers below. It says completing all 22 scored requirements is not expected, while listing 30 identifiers (F1-F8, A1-A8, L1-L6, D1-D8); this matrix preserves every listed identifier. A feature is not complete merely because a file exists. Statuses reflect evidence from this workspace.

| ID | PDF requirement | Implementation | Evidence / status |
|---|---|---|---|
| F1 | REST interface and published contract | `backend/main.py`, `docs/api-contract.md` | API contract implemented; TestClient smoke pass |
| F2 | Boundary validation and quarantine | `backend/schemas.py`, `backend/main.py`, `backend/models.py` | Validation/quarantine + field errors; tests pass |
| F3 | Domain/entity extraction | `backend/orchestrator/graph.py`, `backend/agents/research.py` | Domain classification and typed supplied-fact handoff; free-text extraction partial |
| F4 | Retrieve governing provision/status | `backend/rag/retriever.py`, `backend/agents/verification.py` | Gazette/FAQ indexed; statutes absent; end-to-end status check partial |
| F5 | Cited advisory, every assertion tied to provision in force | `backend/orchestrator/graph.py`, verifier | Fail-closed; no advisory until primary statute is indexed |
| F6 | Three-way decision and basis | `backend/orchestrator/graph.py` | Answer, request-detail and counsel paths implemented; citation answer gated |
| F7 | Escalate termination, harassment, conflict | `backend/orchestrator/graph.py` | Harassment/termination keywords route; conflict detection partial |
| F8 | Health, metrics, structured pipeline logs | `/health`, `/ready`, `/metrics`, run trace | Structured API/run logs, request histograms, DB-derived run/agent gauges and persisted node trace; OTel and all-service telemetry partial |
| A1 | LangGraph/CrewAI agent chooses retrieval tools; bounded calls/time | `backend/agents/research.py`, `backend/orchestrator/graph.py` | Executable graph, conditional tool policy, max 4 tools and 5 seconds per research pass, one retry; policy is deterministic, not model-planned |
| A2 | Two agents, handoff, failure behavior | `backend/agents/`, `docs/agent-topology.md` | Distinct typed research and verification agents, handoff and fail-closed error route; same worker process, not independent service deployments |
| A3 | Verify each assertion/citation against passages | `backend/agents/verification.py` | Official host/version/status/date and unique retrieved citation checks; claim entailment is not implemented; no statutory answer tested |
| A4 | FastAPI async run ID/status and queue | `backend/main.py`, `backend/workers/` | Run ID/status/result/trace/history, Celery production queue and local thread fallback; queue service not live-tested |
| A5 | Per-call timeouts, bounded backoff, breaker, graceful fallback | `backend/llm/provider.py`, `backend/reliability.py`, Celery config | Provider wrapper retries and breaker have unit coverage; provider is not called for legal generation; no live outage demo |
| A6 | Dashboard agent metrics/latency/retries/uptime | `frontend/src/App.tsx`, `monitoring/grafana/provisioning/dashboards/` | UI trace/history and Grafana API/agent/cache panels; container uptime/resource dashboard and live Grafana validation absent |
| A7 | Scale workers and measure effect | `docker-compose.yml`, `locustfile.py` | Local stub-backed 20-user Locust result recorded; Compose worker scaling effect remains unmeasured because Docker engine is unavailable |
| A8 | Web submit/result/citations/escalation | `frontend/src/App.tsx` | Working submit/poll/history/citation/escalation/feedback views; local HTTP smoke passed; verified citation view empty without primary law |
| L1 | LangChain retrieval, Chroma/FAISS, re-embedding | `backend/rag/` | Section-aware PDF ingest with overlap, exact-source lexical retrieval, optional Chroma/Sentence Transformer hybrid and re-embedding; vector runtime unverified |
| L2 | Versioned prompts, log version, compare variants | `backend/prompts/`, run model | Prompt registry and run field; no substantive comparison |
| L3 | 20+ cases, four metrics, before/after | `backend/evaluation/`, `docs/evaluation-report.md` | 20 cases, machine output and routing/retrieval metrics; no generated answers or valid prompt comparison; four answer metrics N/A; context comparison is summary-level |
| L4 | Injection/output/toxicity safeguards | `backend/guardrails.py`, `backend/main.py`, `backend/schemas.py` | All free-text request fields screened and quarantined; abstention utility exists but generated claims do not use it; toxicity detection absent |
| L5 | Provider token/cost per step/run and per 100 | `backend/llm/provider.py`, `backend/workers/` | Token fields exist; advisory graph makes no provider calls and no cost attribution/report exists |
| L6 | Persist/aggregate feedback and score live samples | `/feedback`, `Feedback` model, Grafana metrics | Rating/comment stored; low rating requires comment; aggregates are exposed; live sample auto-scoring/quality-over-time incomplete |
| D1 | External contracts; errors stored; invalid request never starts | schemas, quarantine handler | Field-level validation errors/hash stored; tests pass |
| D2 | Idempotent CLI ingest, version/freshness/throughput metrics | `backend/rag/cli.py`, ingestion helper, `/metrics` | Idempotent JSONL, checksums, indexed time, versions, chunks and measured CLI throughput; corpus freshness not exported as Prometheus metrics |
| D3 | Four+ Compose services, health checks and boundaries | `docker-compose.yml`, docs | Config parses; API/DB/Redis/worker/UI/monitoring services; daemon startup unverified |
| D4 | No checked-in credentials/endpoints/model IDs; runtime config | `.env.example`, config | Sensitive values blank and `.env` ignored; Compose internal service settings remain |
| D5 | JSON logs, correlation, OTel, scrape all services, full trace | trace endpoint, Prometheus, Jaeger, Grafana | JSON API/run logs, tool/node/passage/version/verification trace, API scrape and Grafana dashboard; OTel, every-service scrape, resource metrics and cost gaps |
| D6 | Predeclared complete-run SLO and Locust stub results | `docs/performance-report.md`, `locustfile.py` | SLO declared; local stub-backed 20-user/30-second benchmark completed with zero failures and complete-run p95 2.6 seconds; Docker deployment unavailable |
| D7 | Cache and per-client rate limit; measured effect | `backend/reliability.py`, middleware, retriever | Corpus-version-sensitive retrieval cache and per-client limiter; hit/miss/latency metrics, cache-on/off impact unmeasured |
| D8 | Two failure runbook and genuine incident | `docs/runbook.md`, `docs/incident-log.md` | Runbook and two real incidents documented |

## Demonstration checklist

| # | Demonstration | Status |
|---|---|---|
| 1 | Compose from clean clone | Compose parses and live stack runs; clean-clone deployment not separately tested |
| 2 | Cited advisory | Blocked pending primary statute download/index |
| 3 | Full trace including cost | Tool/passage trace present; cost/OTel missing |
| 4 | Malformed request quarantined, no run | Tested |
| 5 | Unanswerable question escalated | Tested |
| 6 | Unsupported answer caught/retried/escalated | Fail-closed logic tested; adversarial answer fixture partial |
| 7 | Injection quarantined | Tested |
| 8 | Provider circuit breaker + degradation | Utility only, provider outage demo pending |
| 9 | Locust, worker scaling and SLO | Local 20-user stub-backed load passed the 30-second p95 SLO; Docker worker scaling remains unmeasured |
| 10 | Fixed-term 18-month scenario | Official notification/FAQ indexed; primary Section 53 missing, so safely escalates |
# Acceptance evidence update (2026-10-28)

The tables above preserve the original assignment requirement IDs and implementation descriptions. Earlier `pending/unavailable` wording is superseded by this runtime update:

| IDs | Current verification |
|---|---|
| F1-F2, D1 | 26 backend tests pass; live API request/poll/history/trace exercised; validation/quarantine tests pass |
| F4-F5, L1-L2, D2 | `rag.cli --check`: 3 local official sources, 58 chunks; Gazette commencement answer cited live; statutory Code/POSH/Gratuity texts missing, so gratuity answer blocked |
| F6-F7 | Safe routes tested; live gratuity case escalated without citation; claim entailment and full domain legal validation remain incomplete |
| F8, A6, D5 | API metrics and persisted trace verified; Prometheus/Grafana/Jaeger containers are running; OTel app spans not demonstrated |
| A1-A4, D3 | Live LangGraph request completed through Redis/Celery and PostgreSQL; migration revision applied; async trace persisted |
| A5 | Provider abstraction and deterministic mocks tested; Gemini/LangSmith live credentials absent |
| A7, D6 | Historical 20-user local stub test passed; live Compose worker scaling was not benchmarked |
| A8 | Vite production build and live HTTP 200; no browser automation suite |
| L3 | 20 deterministic scenarios: outcome accuracy .95, escalation/clarification correctness 1.0, retrieval precision/recall 0.0, context relevance .1426; no generated answer-quality measurements |
| L4-L6, D4, D7-D8 | Input guards, feedback API, environment-only settings and runbook present; output toxicity, authentication, production DB credentials/TLS, and measured cache/cost effects remain open |

Final disposition: **FUNCTIONALLY COMPLETE WITH EXTERNAL BLOCKERS**. The assignment's critical fixed-term gratuity answer is not passed. See [`FINAL_ACCEPTANCE_REPORT.md`](FINAL_ACCEPTANCE_REPORT.md) for evidence, URLs, source status and reproduction commands.
