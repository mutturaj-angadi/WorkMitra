# Agent topology and hand-off

ResearchAgent returns a Pydantic-validated evidence bundle, supplied case fields and tool records. It conditionally selects section lookup, lexical corpus search and related-provision search; each pass is limited to four calls and five seconds. VerificationAgent independently checks exact text, stable chunk IDs, official host, source version, active statutory status and effective dates, then returns a typed result. A failed first check triggers one query-derived retry; failure afterward routes to counsel review. Both agent interfaces run as separate classes/nodes within one process; they are not separately deployed services, and there is no claim-level entailment checker.

```mermaid
sequenceDiagram
 participant API
 participant R as Research agent
 participant C as Corpus tools
 participant V as Verification agent
 API->>R: question + validated facts
 R->>C: selected search calls
 C-->>R: exact passages + metadata
 R-->>V: evidence bundle
 V-->>R: insufficient / verified
 opt one bounded retry
 R->>C: query-derived provision/exception search
 C-->>R: second-pass passages
 R->>V: re-verify evidence
 end
 V-->>API: status and citation checks
 API-->>API: answer only when verified; otherwise escalate
```
