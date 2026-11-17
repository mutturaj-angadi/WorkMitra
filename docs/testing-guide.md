# Testing guide

## Deterministic backend tests

Tests use isolated corpus roots under `backend/tests/fixtures/` and temporary directories rooted from the test file's absolute path. They do not read `corpus/`, generated ingestion files, `.env` secrets, Gemini, LangSmith, Docker, or external services. The legal test fixture is a small excerpt of the actual S.O. 5319(E) Gazette notification; its provenance and integrity checks are documented in `backend/tests/fixtures/README.md`. That fixture validates commencement retrieval only. It does not supply the missing Code section 53 text and cannot make a gratuity determination pass.

Run from the repository root in PowerShell:

```powershell
python -m compileall -q backend
python -m ruff check backend
python -m ruff format --check backend
python -m pytest -q -p no:cacheprovider
```

Path-independence check from another working directory:

```powershell
Push-Location $env:TEMP
python -m pytest -q -p no:cacheprovider "C:\SEM 5\MLOPs-Mini Project\backend\tests"
Pop-Location
```

The pytest configuration is discovered from the repository's `pyproject.toml`; fixture locations are resolved from `__file__`, not the current directory.

## Frontend production build

```powershell
Push-Location frontend
npm.cmd ci
npm.cmd run build
Pop-Location
```

`npm ci` installs the exact frontend dependency lock. Backend CI uses the explicit project-supported Python 3.13 runtime and installs `requirements-ci.lock` with hash checking. Regenerate that lock intentionally from `requirements-dev.txt` using `pip-compile --generate-hashes --allow-unsafe --output-file requirements-ci.lock requirements-dev.txt`, review the diff, and verify the workflow before updating it.

## Corpus and deterministic evaluation

These are separate integration checks, not prerequisites for unit tests:

```powershell
python -m backend.rag.cli --check
python -m backend.evaluation.run_eval
```

The CLI reads the production manifest and currently available official PDFs, then regenerates ignored `corpus/ingested/*.jsonl`. The evaluation measures routing and retrieval, not generated legal-answer quality. Docker syntax/runtime checks and provider probes are optional external-service checks; do not mix them into deterministic unit tests.

## API smoke checks

Start the local API with `python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000` and use `http://127.0.0.1:8000/docs`. Use synthetic data only. The provider probe is a live external call and is not part of pytest.

## Locust

The Locust task submits and polls until the complete run finishes or its client deadline expires. It is a manual performance profile, not part of CI:

```powershell
$env:LLM_PROVIDER = "stub"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
python -m locust -f locustfile.py --host http://127.0.0.1:8000
```

Do not treat stub results as legal-quality or live-Gemini evidence. See `docs/performance-report.md` for recorded setup and results.
