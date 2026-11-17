# Deployment status

## Verified local setup

The latest local runtime check used SQLite and a local background thread with the API on port 8000 and Vite UI on port 5173. The health/readiness endpoints, API documentation, frontend HTTP response, and frontend-to-API proxy responded. Docker Engine was unavailable in that environment, so Compose services were not runtime-verified.

Start and inspect the local setup from PowerShell at the repository root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\scripts\start-local.ps1
.\scripts\check-health.ps1
```

Open `http://127.0.0.1:5173` and `http://127.0.0.1:8000/docs`. Stop only processes started by the helper:

```powershell
.\scripts\stop-local.ps1
```

## Optional Compose topology

`docker-compose.yml` defines a multi-service deployment path with PostgreSQL, Redis/Celery, frontend/API, Chroma, and monitoring. Availability in configuration is not evidence of runtime health. Check Docker first, then verify services individually with `docker compose ps` and their health endpoints before describing them as running. Do not remove volumes to resolve startup problems; they may contain application data.

The current Compose database configuration is for a local prototype. Before deployment beyond a trusted local machine, configure strong database credentials, TLS, authentication/authorization, secret management, network restrictions, backups, and alerts. The app has no user authentication or authorization and must not be exposed publicly.

## Current status limits

- Docker/Compose service health: not verified in the latest runtime pass.
- Chroma and semantic retrieval: not configured/verified.
- OpenTelemetry export to Jaeger: not verified.
- Gemini provider: configured, but the actual probe timed out with `DEADLINE_EXCEEDED`.
- LangSmith: a synthetic application request was found in the configured project.
- The statutory primary sources needed for gratuity/POSH conclusions remain incomplete; those cases must fail closed.

See [final acceptance report](FINAL_ACCEPTANCE_REPORT.md) for timestamped evidence and [security](security.md) for prototype constraints.
