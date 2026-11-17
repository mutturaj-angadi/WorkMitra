# Development Progress

**Last verified:** 2026-11-16 (Asia/Calcutta)

## Runtime verification complete

- Inspected provider settings without printing secrets: Gemini (`gemini-3.8-flash`), Google/LangSmith key fields non-empty, tracing enabled, mock inactive.
- Used `scripts/start-local.ps1` to start the local API and frontend. Verified API health, readiness, provider health, API docs HTTP 200, frontend HTTP 200, and the Vite proxy response.
- Corrected startup-script argument quoting for the Vite entrypoint, saved process metadata as soon as each process starts, and prevented stale healthy endpoints from masking a newly failed process.
- Corrected and verified `scripts/stop-local.ps1`: it checks recorded PID, executable path, and start-time ticks before stopping. Its test released both local ports.
- A real Gemini probe reached the configured SDK but ended with `_InactiveRpcError` / `DEADLINE_EXCEEDED`; no response arrived. The API remained in Gemini mode and did not silently use mock.
- A real synthetic app request was found in the configured LangSmith project. Added process-level tracing configuration and an explicit `tracing_v2_enabled` context around graph execution. Six recent root/child trace entries matched the synthetic request.
- Ran six workflow categories: Gazette date question, maternity with missing facts, 18-month fixed-term gratuity, POSH, unsupported section, and prompt injection. Maternity clarified; POSH escalated; gratuity and unsupported-section cases escalated with zero verified citations; injection returned HTTP 422 and its quarantine record persisted. The broad Gazette question also escalated because its required notice passage was not retrieved.
- Confirmed run status/result and agent events persisted in local SQLite. The basic Gazette run included classification, fact checking, research, verification, retry, and decision events.
- Corpus CLI: 6 manifest sources, 3 locally ready, 3 missing, 58 chunks, no ingestion failures; the 3 local PDFs passed signature/checksum checks, with no duplicate PDF groups. No embedding model/vector index is configured.
- Evaluation: 30 deterministic scenarios, outcome accuracy 29/30, classification accuracy 21/28, escalation and clarification correctness 1.0 each, retrieval precision/recall 0.0, answer-run denominator 0. G05 (fixed-term gratuity) correctly fails closed and is not a passing legal answer.
- Combined test script: 43 backend tests passed; Ruff lint/format, Python compilation, `pip check`, and frontend build passed. PowerShell scripts parse successfully. One upstream `python_multipart` pending-deprecation warning remains.
- Local performance profile: 20 Locust users, 30 seconds, isolated SQLite and fixed-response stub. 1,321 HTTP requests; zero reported request failures; 122 submissions and 107 measured complete runs. This is a stub-only local profile.
- Docker engine and browser-control host were unavailable. Docker services and visual browser QA were not tested.

## Current blockers

1. Gemini calls time out with `DEADLINE_EXCEEDED`; credentials have not been validated by a successful model response.
2. Primary legal text for the Code on Social Security, POSH Act, and historical Payment of Gratuity Act is missing. Fixed-term gratuity remains counsel-only.
3. Broad Gazette commencement/date phrasing has a retrieval gap; the live request failed closed.
4. Semantic retrieval is not configured. Docker/Compose services were not available.
5. Browser automation host unavailable; only HTTP delivery and proxy behavior were checked.

## Artifacts

- [`docs/FINAL_ACCEPTANCE_REPORT.md`](docs/FINAL_ACCEPTANCE_REPORT.md): live results, workflow dispositions, provider and trace status, evaluation and startup commands.
- [`docs/FINAL_COMPLETION_PLAN.md`](docs/FINAL_COMPLETION_PLAN.md): acceptance matrix and priority follow-up.
- [`docs/known-limitations.md`](docs/known-limitations.md): user-facing limitations.
- [`docs/evaluation-results.json`](docs/evaluation-results.json): 30-scenario machine-readable metrics.
- [`docs/performance-live-stub-2026-11-16_stats.csv`](docs/performance-live-stub-2026-11-16_stats.csv): current local load results.

## Start and stop locally

From the repository root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\scripts\start-local.ps1
.\scripts\check-health.ps1
# Open http://127.0.0.1:5173 and http://127.0.0.1:8000/docs
.\scripts\stop-local.ps1
```

The current `.env` selects Gemini. The provider probe is expected to show the deadline failure until outbound/provider access is resolved.

## Release verification update (2026-11-17)

The release polish pass reran `python -m compileall -q backend`, `python -m pytest -q -p no:cacheprovider` (43 passed; one upstream pending-deprecation warning), Ruff check/format (40 files already formatted), `pip check` (no broken requirements), and `npm.cmd run build` (passed). The corpus CLI again reported 6 manifest entries, 3 ready, 3 missing, 58 chunks, and no failed extractions. A fresh deterministic evaluation produced 29/30 outcome accuracy, 21/28 classification accuracy, 1.0 escalation/clarification correctness, 0.0 retrieval precision/recall, and 22.372/55.96 ms mean/max latency. This is routing/retrieval evaluation, not legal-answer quality.

## GitHub release verification (2026-11-17)

- Published the public repository at `https://github.com/mutturaj-angadi/WorkMitra`, branch `main`; initial release commit `00bd3be0b1df696da163bf1cf26925b2dec15c8f` includes 125 project files and all seven original screenshots. Follow-up commits add CI configuration updates.
- GitHub Actions frontend production build passed. Backend compilation, Ruff lint, and Ruff formatting passed, but backend pytest failed in GitHub Actions under Python 3.11 and 3.13. The same 43-test suite passes locally on Python 3.13. GitHub denied access to backend job logs because the connection lacks repository-admin log permission, so the exact failing assertion could not be recovered. Hosted CI is **not green** and needs follow-up with an admin-visible job log.
- `.env`, local database, build output, dependency folders, caches, and runtime artifacts were excluded. A high-confidence staged-text credential scan found no candidate secrets. Seven supplied screenshots were copied unchanged and committed.
- Release polish added a README gallery and system/workflow/RAG/outcome diagrams. Deployment and retrieval documentation distinguish verified local behavior from optional or unavailable Compose services.
