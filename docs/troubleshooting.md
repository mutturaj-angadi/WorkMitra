# Troubleshooting

## PowerShell blocks the startup script

From the repository root, allow scripts only for the current PowerShell process and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\scripts\start-local.ps1
```

This does not change the machine-wide execution policy.

## Port 8000 or 5173 is occupied

The startup script reports the owning PID and reuses only a responding app; it does not kill unknown processes. Inspect a PID with:

```powershell
netstat -ano | findstr ":8000 :5173"
Get-Process -Id <PID> | Select-Object Id,ProcessName,Path,StartTime
```

If the process is one started by this project, run `scripts/stop-local.ps1`. Otherwise, stop it using its own application controls or choose a free port after adjusting the corresponding app config; do not terminate an unrelated PID.

## API fails to become ready

Check `logs/local/api.stderr.log` and `logs/local/api.stdout.log`. Confirm `.env` exists and explicitly selects `gemini`, `mock`, or `stub`. Gemini mode requires a non-empty Google key and model; enabled tracing requires a LangSmith key. The scripts print only provider/model and non-secret settings.

Health endpoints:

```powershell
.\scripts\check-health.ps1
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
```

`legal_corpus_ready=false` with `mode=fail-closed` means missing primary sources; the API can still be healthy while refusing unsupported legal answers.

## Gemini probe times out

Use `scripts/check-health.ps1 -ProbeProvider`. The current verified result is `_InactiveRpcError` / `DEADLINE_EXCEEDED`, with no response and no fallback to mock. Check outbound connectivity, provider availability, model access, and key restrictions in the local environment. The endpoint intentionally omits raw SDK messages and credentials.

## No LangSmith trace appears

Check `/api/v1/provider/health` for tracing-enabled and configured project flags. The app configures LangChain tracing when the API/worker starts and explicitly wraps graph execution. A provider-health check alone is not an application trace; submit a synthetic request, wait for completion, and query the configured LangSmith project. Never paste keys into commands or logs.

## A run escalates or citations are absent

Read `/api/v1/compliance/runs/{run_id}` and `/trace`. The verifier may reject FAQ guidance, inactive provisions, missing dates, unavailable statutory sections, or passages that do not contain required facts. Check the source manifest and corpus report:

```powershell
python -m backend.rag.cli --check
python -m backend.rag.cli --verify-sources --duplicates
python -m backend.rag.cli --retrieval-test "<synthetic query>"
```

Do not bypass verification. The current Code on Social Security, POSH Act, and Gratuity Act sources are missing, and the fixed-term gratuity question must stay with counsel.

## Frontend loads but reports API unavailable

Open `http://127.0.0.1:5173/api/v1/ready` to test the Vite proxy. If it fails, start the API first and inspect the backend logs. `http://127.0.0.1:8000/docs` should return HTTP 200 when the API is listening.

## Tests or build fail

Run `scripts/run-tests.ps1` from the repository root. It checks pytest, Ruff lint/format, Python compilation, dependency consistency, and frontend production build. A known upstream `python_multipart` pending-deprecation warning does not fail the current suite.

## Docker services unavailable

Docker Compose requires a running Docker Desktop Linux engine. The latest environment had no Docker engine pipe, so PostgreSQL/Redis/Celery/Chroma/monitoring checks were not run. Local development uses SQLite; do not report Compose as healthy until `docker compose ps` and service health checks succeed.
