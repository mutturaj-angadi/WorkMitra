# Architecture

## Current local workflow

```mermaid
flowchart LR
  UI[React and TypeScript UI] -->|HTTP / Vite proxy| API[FastAPI]
  API --> VAL[Validation and quarantine]
  VAL --> DB[(SQLite local)]
  VAL --> GRAPH[LangGraph workflow]
  GRAPH --> CLASS[Classification and missing-fact checks]
  CLASS --> RESEARCH[Research node]
  RESEARCH --> RAG[Lexical retrieval]
  RAG --> CORPUS[Manifest-verified local PDFs]
  RAG -. optional .-> CHROMA[(Chroma and local embedding model)]
  GRAPH --> VERIFY[Independent citation and evidence verifier]
  GRAPH -. optional query planning only .-> GEMINI[Gemini provider]
  API -. deployment option .-> RC[Redis and Celery]
  PROM -. optional, not verified .-> GRAFANA[Grafana]
  API -. optional, not verified .-> OTEL[OpenTelemetry exporter]
  OTEL -. optional, not verified .-> JAEGER[Jaeger]
  VERIFY -->|verified evidence| RESULT[Source-supported response]
  VERIFY -->|insufficient/conflicting evidence| ESCALATE[Human/legal review]
  GRAPH -. configured .-> LANGSMITH[LangSmith trace]
  API --> PROM[Prometheus metrics endpoint]
```

Locally, the API uses SQLite and a background thread. The workflow includes request classification, fact sufficiency checks, research, citation/source/date validation, a bounded retry, and safe outcome routing. Prompt-injection-like input is quarantined before workflow execution. Runs and workflow events persist in SQLite.

Gemini is configured as an optional provider for query planning; it does not decide legal conclusions. In the latest verification it timed out with `DEADLINE_EXCEEDED`, and the application stayed in Gemini mode without silently falling back to mock. LangSmith was enabled; a synthetic application request was found in the configured project.

## Configured deployment path

The Compose configuration includes PostgreSQL, Redis/Celery, frontend/API, Chroma and monitoring services. These services were not runtime-verified in the latest environment because Docker Engine was unavailable. Chroma/embeddings and OpenTelemetry export are optional and not claimed as operational. SQLite is the verified local persistence path.

## Evidence and current limits

The local source manifest has six entries: three validated PDFs and 58 extracted chunks, with three primary legal PDFs missing (Code on Social Security, POSH Act, and historical Payment of Gratuity Act). The independent verifier fails closed; the fixed-term gratuity scenario routes to counsel while primary statutory evidence is absent. See [legal sources](legal-sources.md), [RAG pipeline](rag-pipeline.md), and [final acceptance report](FINAL_ACCEPTANCE_REPORT.md).

## Outcome routing

```mermaid
flowchart TD
  START[Classified request] --> GATE{Required establishment facts present?}
  GATE -->|No| MORE[REQUEST_MORE_ESTABLISHMENT_DETAIL]
  GATE -->|Yes| REVIEW{Sensitive case or unsupported law?}
  REVIEW -->|Yes| COUNSEL[LEGAL_COUNSEL_REVIEW]
  REVIEW -->|No| EVIDENCE{Exact primary evidence verified?}
  EVIDENCE -->|Yes| ANSWER[ANSWER_WITH_CITATION]
  EVIDENCE -->|No or conflicting| COUNSEL
```

The request layer quarantines unsafe or identifier-like input before workflow execution. SQLite/PostgreSQL records describe local/deployment paths; SQLite is the persistence path verified in the latest local runtime check.
