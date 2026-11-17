# Incident log

## 2026-10-28 — Frontend package peer dependency conflict

- **Symptom:** `npm.cmd install` failed with `ERESOLVE`: the floating `@vitejs/plugin-react@latest` resolved to a release requiring Vite 8, while the project declared Vite 6.
- **Impact:** Frontend dependencies could not be installed, so the production build was initially blocked.
- **Confirmation:** npm's resolver named the incompatible `vite@6.4.5` and `@vitejs/plugin-react@6.1.2` peer requirement.
- **Recovery:** Pinned the React plugin to the compatible 4.x line, installed packages, generated a lockfile, and then `npm.cmd run build` passed.
- **Follow-up:** Keep the lockfile and use `npm ci` in the frontend container.

## 2026-10-28 — Official corpus downloads unavailable

- **Symptom:** Publisher PDF download attempts transferred zero bytes and timed out after 20 seconds.
- **Impact:** The primary Code, POSH and historical gratuity PDFs remain absent. Three official notification/guidance documents remain indexed, but the statutory-answer case fails closed.
- **Confirmation:** India Code Python `urllib` requests timed out before receiving bytes. An alternate Ministry URL referenced in an official Ministry letter redirected to a not-found response. No invalid placeholder files were retained.
- **Recovery:** Kept official source URLs in the manifest and the retryable `python -m backend.rag.cli --download` ingestion path; distinguished web source discovery from local source ingestion in the source register.
- **Follow-up:** Retry when publishers serve the files; validate PDF signature/text and exact section chunks, then run the fixed-term case. Do not substitute bill text or search snippets for the current Act.

## 2026-10-28 — Docker Desktop Linux engine unavailable

- **Symptom:** `docker info` could not open `npipe:////./pipe/dockerDesktopLinuxEngine`.
- **Impact:** No image build, live service startup, connectivity check or Locust scaling test could be performed.
- **Confirmation:** The CLI reports that the named pipe does not exist. `docker compose config --quiet` still parses successfully; that is configuration validation only.
- **Recovery:** Documented Windows Docker Desktop startup and verification steps in `docs/deployment.md`; the local backend and frontend are validated separately.
- **Follow-up:** Start Docker Desktop's Linux engine, rerun `docker info`, then execute Compose build/up/ps/health and Locust measurements.
# 2026-10-28 — Compose and worker integration resolved

- **Issue:** Initial Compose attempt used a non-existent Jaeger image tag; the deployed image tag was corrected. On first live Celery request, the queue accepted the task but worker had not registered `backend.workers.tasks.process_run`.
- **Cause:** Celery app did not include the worker task module in its imports.
- **Resolution:** Added explicit task discovery in `backend/workers/celery_app.py`; rebuilt/restarted containers; worker advertised the task and completed a live request. Persisted trace contained 20 events from three graph agents.
- **Other issue:** Extracted JSONL corpus was excluded by `.dockerignore`, so runtime image lacked Gazette chunks. Removed the stale exclusions, reran ingestion, rebuilt images, and verified a live citation to S.O.5319(E).
- **Database:** Added an Alembic additive baseline; existing PostgreSQL volume adopted without data deletion.
