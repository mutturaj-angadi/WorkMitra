# Testing guide

## Offline checks (Windows PowerShell)

From the repository root:

```powershell
python -m pytest -q -p no:cacheprovider
python -m compileall -q backend
python -m ruff check backend
python -m pip check
Set-Location frontend
npm ci
npm run build
Set-Location ..
python -m backend.rag.cli --check
python -m backend.evaluation.run_eval
python -m json.tool monitoring/grafana/provisioning/dashboards/compliance-desk.json > $null
docker compose config --quiet
```

The evaluation command writes `docs/evaluation-results.json`. `docker compose config` validates syntax and variable resolution only; see `docs/deployment.md` before reporting live deployment.

## API smoke checks

Start the backend with `python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000` and use `http://127.0.0.1:8000/docs`. The Pytest suite covers validation/quarantine, request submission, run/status/history/trace, feedback, metrics, agent retry and fail-closed verification. A live smoke was also run against the 18-month assignment scenario; it completed with counsel escalation because primary Section 53 is missing.

## Locust

The Locust task submits and polls until the complete run finishes or a 40-second client deadline expires. It emits a custom complete-run timing event. Start the backend with the stub enabled in one PowerShell window:

```powershell
$env:LLM_PROVIDER = "stub"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then run Locust from a second window:

```powershell
python -m locust -f locustfile.py --host http://127.0.0.1:8000
```

Do not use the Locust results as generated-answer or legal-quality evidence. Record concurrency, complete-run RPS/p50/p95/errors, worker count and stub delay. A local 20-user/30-second stub-backed run is available in `performance-report.md` and `performance-20users_*.csv`; it met the p95 target. Docker is now live and a single async worker path was verified, but Compose load/scaling measurements remain unrun.

Current automated verification: 26 pytest tests passed; Ruff check/format and Python compile passed; Vite production build passed. The evaluation runner executed 20 deterministic scenarios. Citation-quality/faithfulness/hallucination metrics remain not measured because the workflow generated no substantive statutory answer runs.
