# Agent Workflow

## Request path

1. **API guard:** validates request shape and checks every user free-text field for prompt injection or identifier-like content. Unsafe input is quarantined with a digest and field-level reasons; the workflow is not started.
2. **Persistence and queueing:** accepted requests and a `QUEUED` run are committed to SQLAlchemy before the HTTP 202 response. Local development uses a background thread; production settings can dispatch to Celery.
3. **Classification:** maps the request to a supported domain using the explicit domain or deterministic text rules.
4. **Fact gate:** checks coverage facts for maternity requests. Missing establishment type/headcount returns `REQUEST_MORE_ESTABLISHMENT_DETAIL` without legal research.
5. **Human-review gate:** harassment complaints and termination disputes route to `LEGAL_COUNSEL_REVIEW` before research.
6. **Research:** `ResearchAgent` gathers request fields and searches the checked-in JSONL corpus. When Gemini is enabled, it may propose at most one search phrase. The model is not asked to answer, invent law, or choose the outcome. A provider failure is recorded safely and lexical search continues. Optional semantic retrieval is available only when an embedding model and Chroma are configured.
7. **Verification:** `VerificationAgent` independently checks exact source text, stable chunk ID, source host/version, active status, effective dates, document type, citation provenance, and special gratuity prerequisites. The Ministry FAQ cannot substitute for missing Code section 53 text.
8. **Retry and decision:** insufficient evidence gets one bounded query-derived second search and another verification. Only verified evidence can produce `ANSWER_WITH_CITATION`; missing/invalid evidence routes to counsel. Facts-only gaps can route to clarification.
9. **Persistence and observability:** completed run result, decision, evidence, graph node events, tool calls, and verification are written to SQLite/PostgreSQL. The trace endpoint reads these events. When enabled, graph execution also uses an explicit LangSmith tracing context.

## Current runtime boundaries

- Gemini is a query planner only. A real request was attempted, but `DEADLINE_EXCEEDED` prevented a model response.
- Local app mode uses SQLite and a background thread. Docker services were not available in the latest run.
- Three official sources and 58 chunks are available; three primary Acts are missing. Readiness remains fail-closed.
- The stored workflow trace proves agent execution/persistence. It does not establish that the generated answer is legally complete.

## Acceptance invariants

- Never let user input or planner output alter verification rules.
- Never create a citation that is not one of the exact retrieved passages.
- Never present the fixed-term gratuity case as answered until current primary text and all required facts are verified.
- Never turn a model outage, missing corpus item, or failed verification into a guessed answer.
