# Viva Preparation

Use these answers as a concise guide. State the observed limits directly; do not present a fail-closed prototype as a complete legal advisory service.

## Design questions

### 1. What problem does the project address?

It provides an HR-facing intake and evidence-retrieval workflow for workplace compliance questions. It validates and classifies synthetic questions, retrieves local official text, verifies provenance, and escalates when evidence or facts are missing.

### 2. Does it give legal advice?

No. It is a statutory information and triage prototype. The verifier can only support a narrow information response from retrieved evidence; unsupported cases go to qualified human review.

### 3. Why use multiple agents?

Research and verification have separate responsibilities. Research retrieves passages and records search activity; the verifier checks exact text, source, status, dates, and citation identity. They are separate Python components in one LangGraph workflow, not separate microservices.

### 4. What does LangGraph do here?

It runs typed workflow nodes for classification, missing-fact checks, a human-review gate, research, verification, one retry, and final routing. Node/tool events are persisted for inspection.

### 5. What does Gemini do?

When enabled, Gemini may propose a short search phrase. It is explicitly instructed not to answer or invent legal sources. It does not decide the legal outcome. The latest real provider attempt timed out with `DEADLINE_EXCEEDED`, so successful model output has not been verified.

### 6. What happens when Gemini is unavailable?

The provider reports a sanitized failure. The application remains in Gemini mode; it does not silently switch to mock. Research can continue with lexical queries, and the verifier still determines whether evidence is sufficient.

### 7. What is RAG in this project?

PDFs are extracted into section/page-aware JSONL chunks with source and date metadata. Current local search is lexical. Optional semantic search requires a configured embedding model and Chroma, neither configured in the latest environment.

### 8. How are citations validated?

The verifier checks that the metadata belongs to an actual retrieved chunk and validates approved host, source version, legal status, effective dates, stable chunk ID, and required statutory provisions. A citation is not created from model output.

### 9. What is fail-closed behavior?

When required source text, dates, or facts cannot be verified, the system does not guess. It returns a clarification or counsel route. The 18-month gratuity case correctly reaches counsel because primary Code section 53 is missing.

### 10. How is prompt injection handled?

The API inspects free-text input before starting the workflow. Detected injection or identifier-like content is quarantined; a digest and field errors are stored, and the raw suspicious text is not passed to an agent.

## Runtime and MLOps questions

### 11. Which database is used locally?

SQLite is used for local development, with a background thread. The intended production path can use PostgreSQL and Redis/Celery, but Docker services were not available during the latest runtime verification.

### 12. How is LangSmith tracing configured?

Validated settings are copied into LangChain's process environment, and graph execution uses an explicit `tracing_v2_enabled` context with the configured project/client. A synthetic live request was found in the project; the trace query found six matching root/child entries.

### 13. What metrics are exposed?

The API exposes Prometheus request/run and retrieval-cache metrics. Compose contains Prometheus/Grafana configuration, but those services were not runtime-tested because Docker was unavailable.

### 14. What tests passed?

Latest result: 43 backend tests, Ruff lint/format, Python compile, pip dependency check, PowerShell script parse, and frontend production build all passed. One Starlette `python_multipart` pending-deprecation warning remains.

### 15. What does the evaluation measure?

Thirty deterministic cases measure routing/classification and lexical retrieval. Outcome accuracy was 29/30 and classification accuracy 21/28. It produced no answers, so answer-level citation completeness, groundedness, faithfulness, and hallucination rates are null/unmeasured.

### 16. What did the load test show?

A local 20-user, 30-second Locust profile with a fixed-response stub and isolated SQLite recorded 1,321 HTTP requests and zero reported failures. It is not evidence of Gemini, Docker, multiworker, or production capacity.

### 17. Why is the corpus incomplete?

Three of six manifest sources are present and checksum-verified: two Gazette notices and one Ministry FAQ. The Code on Social Security, POSH Act, and historical Payment of Gratuity Act were unavailable locally. The system records this gap and abstains.

### 18. Does the project currently answer the gratuity question?

No. It retrieves some related FAQ material but does not have primary section 53 text. The runtime result is `LEGAL_COUNSEL_REVIEW` with no verified citation. This required scenario has not passed as an answer.

### 19. What were the main runtime blockers?

Gemini requests timed out with gRPC `DEADLINE_EXCEEDED`; three legal source PDFs are missing; semantic embeddings are not configured; Docker and browser automation were unavailable. The API/UI local HTTP path and LangSmith tracing for one synthetic request were verified.

### 20. What would you do next?

Resolve Gemini reachability, acquire and checksum-verify the primary legal texts, ingest them without altering legal content, expand retrieval tests around Gazette commencement phrasing, configure embeddings if needed, and repeat live provider, legal workflow, Docker, and browser verification.
