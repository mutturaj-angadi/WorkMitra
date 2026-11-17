# Local Runbook

## Start and check

From the repository root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\scripts\start-local.ps1
.\scripts\check-health.ps1
```

The UI is `http://127.0.0.1:5173`; API docs are `http://127.0.0.1:8000/docs`. The current runtime uses SQLite and a local worker thread. Health can be `ok` while corpus readiness remains `fail-closed`.

## Stop safely

```powershell
.\scripts\stop-local.ps1
```

The script stops only recorded processes whose PID, executable path, and start time match. Do not kill an unrelated PID to resolve a port conflict.

## API is unavailable

Run `scripts/check-health.ps1`, then inspect `logs/local/api.stderr.log` and `logs/local/api.stdout.log`. Check port 8000 and API docs before retrying. If the port owner is not this project's tracked server, stop it through its own application.

## No legal answer

Inspect the result and `/api/v1/compliance/runs/{run_id}/trace`. The current local corpus has three of six sources and does not include the primary Code, POSH, or Gratuity Acts. The 18-month fixed-term gratuity scenario should escalate. Use `python -m backend.rag.cli --verify-sources --duplicates` to inspect corpus state; never bypass the verifier.

## Gemini or LangSmith issue

Use `.\scripts\check-health.ps1 -ProbeProvider` for the one bounded provider request. The latest Gemini result was `_InactiveRpcError` / `DEADLINE_EXCEEDED`; no successful response was received. The application has explicit LangSmith graph tracing; submit and complete a synthetic application request before checking the configured project. No key values are returned by health endpoints.

## Docker services

The latest environment had no Docker engine named pipe. Do not report PostgreSQL, Redis/Celery, Chroma, Prometheus, Grafana, or Jaeger as running until Docker is available and service health is confirmed. No volume deletion is part of normal recovery.
