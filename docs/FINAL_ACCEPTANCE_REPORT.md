# Final Runtime Acceptance Report

**Verification date:** 2026-11-17 (Asia/Calcutta; CI rerun)
**Disposition:** Local runtime verified; live Gemini response and complete legal-source coverage remain blocked.

## Executive summary

The local FastAPI backend and Vite frontend were started with `scripts/start-local.ps1`. The API, documentation page, frontend, and frontend-to-API proxy responded. The shutdown script was also exercised: it stopped only the recorded Python and Node processes and released ports 8000 and 5173. The app is configured for Gemini with mock mode off and LangSmith tracing enabled.

The configured Gemini SDK initialized and made real provider attempts, but the calls ended with gRPC `_InactiveRpcError` / `DEADLINE_EXCEEDED`; no model response was received. The API did not fall back to mock. A LangSmith trace for a synthetic request was later found in the configured project after tracing was wired through an explicit LangChain trace context.

The core workflows ran against local SQLite and persisted their results and agent events. Maternity missing facts routed to clarification; POSH routed to human review; fixed-term gratuity and unsupported Section 53 requests escalated with no verified citation; prompt injection was quarantined. A broad Gazette date question also failed closed. This last result shows that the available Gazette text is not reliably retrieved for every natural-language phrasing.

The corpus has 3 of 6 manifest documents locally verified and 58 chunks. The primary Code on Social Security, POSH Act, and Payment of Gratuity Act remain absent. Chroma embeddings are not configured. The 18-month gratuity scenario remains a **failure to answer safely**, not a successful statutory answer.

## Live runtime evidence

| Check | Observed result |
|---|---|
| Python / Node | Python 3.13.5 / Node 25.1.0 |
| Port 8000 | Backend responded; `/api/v1/health` returned `ok` |
| Port 5173 | Frontend returned HTTP 200 |
| API docs | `http://127.0.0.1:8000/docs` returned HTTP 200 |
| Vite API proxy | `http://127.0.0.1:5173/api/v1/ready` returned backend readiness JSON |
| Database | SQLite |
| Readiness | API ready, `legal_corpus_ready=false`, `mode=fail-closed` |
| Provider config | `gemini`, model `gemini-3.8-flash`, mock mode inactive |
| Credential state | Google and LangSmith key fields were non-empty; key values were never printed |
| LangSmith setting | Enabled; configured project `workplace-compliance-advisory-desk` |

The local UI and backend can be opened at `http://127.0.0.1:5173` and `http://127.0.0.1:8000/docs`. A browser-control host was unavailable, so no screenshot-based visual inspection was possible; HTTP delivery and the Vite proxy were verified instead.

## Gemini provider verification

`POST /api/v1/provider/check` issued real, minimal requests through the configured Gemini provider. The safe failure metadata was:

- Provider: Gemini; model: `gemini-3.8-flash`.
- Failure: `_InactiveRpcError`, gRPC code `DEADLINE_EXCEEDED`; HTTP status unavailable.
- A response was not received. The SDK call did initialize, but the credential was not authenticated by a successful response.
- `mock_mode_active` remained false. There is no silent fallback to mock.

This establishes a provider timeout, but not whether the cause is network reachability, provider availability, or credential restrictions. Do not describe the Google key as validated until a successful response is obtained. The API response and server logs expose only failure type/code/status metadata; they do not expose keys or provider error text.

## LangSmith verification

The first read-only project query returned `Project ... not found` and no application runs. Pydantic had loaded values from `.env`, but the app had not explicitly supplied them to LangChain's tracer. Runtime tracing initialization was added to the API/worker path, and graph execution now uses an explicit `tracing_v2_enabled` context with the configured client and project.

After that fix, a synthetic POSH workflow was submitted and the LangSmith project was read successfully. The project query found **6 recent trace entries matching the request** (root/child trace entries). This confirms trace delivery for the tested request. It does not validate trace delivery for an actual successful Gemini completion.

## Workflow smoke tests

All questions used synthetic text; no personal employee data was submitted.

| Scenario | Runtime result | Verification |
|---|---|---|
| Basic Gazette date question | `COMPLETED`, `LEGAL_COUNSEL_REVIEW` | `INSUFFICIENT_EVIDENCE`; broad wording retrieved 7 passages but 0 verified citations. Safe, but the intended narrow answer was not produced. |
| Maternity question without establishment facts | `REQUEST_MORE_ESTABLISHMENT_DETAIL` | Classified as `MATERNITY_BENEFIT`; graph persisted `classify` and `fact_check` events and requested more information. |
| 18-month written fixed-term gratuity | `LEGAL_COUNSEL_REVIEW` | `INSUFFICIENT_EVIDENCE`; 11 retrieved passages, 0 verified citations. Missing Code section 53 did not produce a legal conclusion. |
| POSH complaint | `LEGAL_COUNSEL_REVIEW` | `ESCALATE`; human-review gate ran before research. |
| Unsupported Code section 53 question | `LEGAL_COUNSEL_REVIEW` | `INSUFFICIENT_EVIDENCE`; 0 verified citations. |
| Prompt injection | HTTP 422, `QUARANTINED` | Returned a quarantine ID; the quarantine record was confirmed in SQLite. No workflow/model run was started. |

Completed run records and agent events were read back through the API. The basic Gazette run persisted 19 events, including classification, fact gate, research, verification, retry, and decision. The fixed-term case persisted research, verification, retry, decision, and retrieval events. The UI API path is same-origin through Vite; the browser automation service itself was unavailable.

## RAG corpus and evaluation

`python -m backend.rag.cli --check` reported **6 manifest sources, 3 ready, 3 missing, 58 chunks, 0 ingestion failures**. `--verify-sources --duplicates` confirmed that the three local PDFs have valid signatures and matching manifest hashes, with no duplicate PDF groups. The missing source IDs are:

- `code-social-security-2020`
- `posh-act-2013`
- `payment-gratuity-act-1972`

`--validate-embeddings` reported `unavailable` with `ValueError`: no embedding model is configured. There is no vector index; observed retrieval is lexical. A Section 53/fixed-term search returned Ministry FAQ chunks, but the verifier correctly rejected them as a substitute for the primary statute.

The 30-case deterministic evaluation is in [`evaluation-results.json`](evaluation-results.json):

| Metric | Result |
|---|---:|
| Outcome accuracy | 29/30 (0.9667) |
| Classification accuracy | 21/28 (0.7500) |
| Escalation correctness | 1.0000 |
| Clarification correctness | 1.0000 |
| Retrieval precision@k / recall@k | 0.0000 / 0.0000 for labeled primary-provision retrieval |
| Safe abstention rate | 1.0000 |
| Mean lexical context relevance | 0.1391 |
| Answer-run denominator | 0 |
| Evaluation latency mean / max | 55.33 / 128.68 ms |

Scenario G05 is the expected fixed-term gratuity answer but actually routes to counsel because section 53 is absent. Citation correctness, citation completeness, groundedness, faithfulness, unsupported-claim rate, and hallucination rate are `null`/not measured; the suite generates no legal answers and these values must not be interpreted as zero-error answer quality.

## Automated and performance checks

`scripts/run-tests.ps1` completed successfully:

- Backend: **43 passed**, one upstream Starlette `python_multipart` pending-deprecation warning.
- Ruff lint and formatting: passed (40 files formatted).
- Python compilation: passed.
- `pip check`: no broken requirements.
- Frontend TypeScript/Vite production build: passed.
- PowerShell parser check for all `scripts/*.ps1`: passed.

An isolated Locust run used 20 users for 30 seconds against a temporary local API using the explicit fixed-response stub, a separate SQLite database, and no LangSmith/Gemini calls. It recorded 1,321 HTTP requests with 0 reported request failures; 122 submissions and 107 complete-run measurements. The 15 submission/complete-run difference is in-flight work at shutdown and is not counted as a completed request. For completed runs, p50/p95 were 3.7/6.4 seconds. Raw CSVs are [`performance-live-stub-2026-11-16_stats.csv`](performance-live-stub-2026-11-16_stats.csv) and companion files. This is a local stub/SQLite profile, not a production, Docker, or Gemini capacity test.

Docker was unavailable: the Docker engine named pipe was absent and the Docker client could not read the host config. No Compose/PostgreSQL/Redis/Celery/Chroma/Prometheus/Grafana/Jaeger runtime check was performed in this pass.

## Outstanding limitations

1. The Gemini provider call times out with `DEADLINE_EXCEEDED`; successful credential validation and real model output remain unverified.
2. The Code on Social Security, POSH Act, and historical Gratuity Act are absent from the local corpus. The critical gratuity answer remains correctly escalated.
3. The broad Gazette date phrasing failed retrieval/verification; its current result was counsel review. Retrieval precision/recall are zero on the labeled suite.
4. No embedding model or vector backend is configured; retrieval is lexical only.
5. No Docker services were available. Authentication, authorization, production TLS/secrets, and production database controls remain outside this local prototype's verification.
6. Browser automation was unavailable; HTTP/UI proxy was checked, but rendered-page behavior was not visually inspected.
7. Generated-answer quality and prompt comparison are not measured because answer generation is not used for legal conclusions.

## Reproduction commands

## GitHub Actions CI verification (2026-11-17)

The corpus-dependent failures were caused by tests reading ignored generated ingestion output. Tests now use committed, provenance-documented fixtures and temporary corpus roots. A first follow-up run exposed a dependency lock generated on Windows that could not install on GitHub's Linux runner; CI now uses the universal `uv.lock` with uv 0.13.8. Run [44041844414](https://github.com/mutturaj-angadi/WorkMitra/actions/runs/44041844414), commit `8352ce68a490393ece0ff004906a5a509d9f4569`, completed successfully for both jobs. Backend dependency sync, compile, Ruff lint/format, and pytest passed; frontend `npm ci` and production build passed. Local pytest result was 47 passed with one upstream deprecation warning. This test result covers deterministic routing/retrieval regressions, not production corpus completeness or legal answer quality.

The CI pytest console output was not needed to diagnose this pass; the successful job step is visible in the run. See [`testing-guide.md`](testing-guide.md) for reproducible local commands and lock maintenance.

In PowerShell at the repository root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\scripts\start-local.ps1
.\scripts\check-health.ps1
.\scripts\check-health.ps1 -ProbeProvider
.\scripts\run-tests.ps1
python -m backend.rag.cli --check
python -m backend.evaluation.run_eval
.\scripts\stop-local.ps1
```

The provider probe is expected to fail until the Gemini `DEADLINE_EXCEEDED` issue is resolved. The shutdown command only stops processes whose PID, executable path, and recorded start time match the local startup state file.
