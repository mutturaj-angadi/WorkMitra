# API contract

All paths are prefixed `/api/v1`.

| Method/path | Purpose |
|---|---|
| POST `/compliance/requests` | Validate and enqueue HR query; HTTP 202 with run ID. Schema errors 422; injection patterns quarantined pre-agent. |
| GET `/compliance/runs/{run_id}` | Status, decision, prompt version and result. |
| GET `/compliance/runs/{run_id}/status` | Polling response. |
| GET `/compliance/runs/{run_id}/trace` | Agent calls and verification events. |
| GET `/compliance/runs?limit=25` | Latest persisted run summaries (limit 1-100). |
| POST `/compliance/feedback` | Rating 1-5 and comment; ratings 1-2 require a reason. |
| GET `/health`, `/ready`, `/metrics` | Liveness, database readiness/corpus state, Prometheus exposition. |

Request fields: question (12-4000 chars), optional domain (`GRATUITY`, `MATERNITY_BENEFIT`, `WORKPLACE_HARASSMENT`, `OTHER`), establishment type, headcount, employment start/end, contract type, idempotency key. End date cannot precede start date. Prompt-injection and identifier checks apply to all free-text request fields; rejected payloads are stored as a SHA-256 digest plus field-level codes, never raw values.
