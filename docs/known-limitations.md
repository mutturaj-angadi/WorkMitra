# Known Limitations

**Updated:** 2026-11-16

## Legal corpus and answer coverage

- Only 3 of 6 manifest sources are present and checksum-verified: Gazette S.O.5319(E), Gazette S.O.5936(E), and the Ministry of Labour FAQ PDF.
- The Code on Social Security, 2020, POSH Act, 2013, and historical Payment of Gratuity Act are missing locally. The 18-month fixed-term gratuity determination must remain escalated until primary section 53 evidence is ingested and independently verified.
- The live basic Gazette date question returned counsel review. Broad natural-language phrasing did not retrieve the chunk needed by the verifier. The narrow Gazette answer path is not accepted as generally verified from this runtime run.
- Labeled retrieval precision@k and recall@k are both 0.0 in the 30-case deterministic evaluation. Lexical context relevance is 0.1391 on average.
- The corpus uses exact-text lexical retrieval. No embedding model is configured, and `--validate-embeddings` reports `ValueError`; Chroma/vector retrieval was not available.
- The evaluation does not generate legal answers: answer-run denominator is zero. Citation correctness, completeness, groundedness, faithfulness, unsupported-claim rate, and hallucination rate are unmeasured/null.

## External providers and tracing

- Gemini is configured as the provider and mock mode is off. The real probe ended in `_InactiveRpcError` with `DEADLINE_EXCEEDED`; no generated response was received and the key's validity is not established.
- No automatic mock fallback occurs. Provider failures are reported without raw SDK messages or credential values.
- LangSmith tracing was verified for a synthetic request after the graph was given an explicit tracing context. This does not establish tracing of a successful Gemini request.

## Runtime and deployment

- The verified path is local Windows development with SQLite and an in-process background thread. Docker was unavailable because the Docker engine named pipe was absent, so PostgreSQL, Redis/Celery, Chroma, Prometheus, Grafana, and Jaeger were not runtime-verified in this pass.
- The app has no user authentication/authorization or production TLS/secret-management hardening. Do not expose the prototype publicly or submit real employee records.
- The frontend returned HTTP 200 and its Vite proxy returned backend readiness. Browser-control was unavailable, so rendered UI behavior was not visually inspected.
- The local stub load test is not a production-capacity or live-Gemini benchmark. It recorded 1,321 HTTP requests, zero reported failures, 122 submissions, and 107 completed-run timings during a 30-second test; the difference is in-flight work at shutdown.

## Reproduction

See [`FINAL_ACCEPTANCE_REPORT.md`](FINAL_ACCEPTANCE_REPORT.md) for exact results and [`FINAL_COMPLETION_PLAN.md`](FINAL_COMPLETION_PLAN.md) for ordered follow-up work.
