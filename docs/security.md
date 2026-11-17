# Security and privacy

- Use synthetic scenarios only; do not enter real employee data.
- Secrets remain backend-side; `.env` is ignored by Git.
- Prompt injection and identifier patterns are checked on the question, establishment type and contract type before agent execution; quarantine stores only a digest and field names. This basic pattern check is not a complete detector.
- Retrieved passages are data, not instructions.
- No response is marked verified without exact text, active status, source URL and version. Empty corpus escalates.
- A per-client in-memory rate limit and provider circuit-breaker wrapper exist, but the provider is not called by advisory generation. Comprehensive output PII/toxicity filtering, authentication/authorization, distributed rate limiting and secret rotation are not implemented; do not expose this prototype publicly.
# Current security verification (2026-10-28)

API runtime settings returns only non-secret config. Docker API/worker use a non-root account. Suspicious/malformed inputs are screened or quarantined using digests and field names. Citation/date/status checks and abstention remain fail-closed. PostgreSQL Compose `trust` authentication is only appropriate for the local prototype; there is no API authentication/authorization or TLS. Do not expose the current deployment publicly. Output toxicity checks, real-provider credential handling tests, OTel span review, backup/restore validation, and production security testing remain incomplete.
