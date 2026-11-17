import hashlib
import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from time import monotonic

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.config import configure_langchain_tracing, get_settings
from backend.database import Base, SessionLocal, engine, ensure_compat_columns, get_db
from backend.guardrails import inspect_input
from backend.llm.provider import get_provider
from backend.models import (
    AgentExecution,
    ComplianceRequest,
    ComplianceRun,
    Feedback,
    QuarantinedRequest,
)
from backend.schemas import (
    ComplianceInput,
    Domain,
    FeedbackInput,
    FeedbackResponse,
    FeedbackSummaryResponse,
    HealthResponse,
    ProviderHealthResponse,
    ProviderProbeResponse,
    ReadinessResponse,
    RunHistoryResponse,
    RunResponse,
    RunStatusResponse,
    RuntimeSettingsResponse,
    SubmitResponse,
    TraceResponse,
)
from backend.workers.tasks import process_run

settings = get_settings()
configure_langchain_tracing(settings)
logger = logging.getLogger("compliance_desk")
app = FastAPI(
    title="Workplace Compliance Advisory Desk API",
    version="0.1.0",
    description="Cited statutory information for compliance assistance; not legal advice.",
)
if settings.app_env != "production":
    Base.metadata.create_all(bind=engine)
    ensure_compat_columns(engine)
REQUESTS = Counter("compliance_requests_total", "Submitted requests", ["outcome"])
RUN_LATENCY = Histogram(
    "compliance_run_queue_seconds", "Time from submission to accepted queue"
)
API_REQUESTS = Counter(
    "compliance_api_requests_total",
    "API requests by route and response",
    ["method", "route", "status"],
)
API_LATENCY = Histogram(
    "compliance_api_request_seconds", "API request duration", ["method", "route"]
)
RUNS_BY_STATUS = Gauge(
    "compliance_runs_by_status", "Persisted runs by execution status", ["status"]
)
RUNS_BY_DECISION = Gauge(
    "compliance_runs_by_decision", "Persisted runs by final decision", ["decision"]
)
AGENT_EVENT_COUNT = Gauge(
    "compliance_agent_events_total",
    "Persisted agent/workflow events by agent and event",
    ["agent", "event"],
)
AGENT_EVENT_LATENCY = Gauge(
    "compliance_agent_event_duration_ms",
    "Persisted agent/workflow event duration quantiles in milliseconds",
    ["agent", "event", "quantile"],
)
FEEDBACK_RATINGS = Gauge(
    "compliance_feedback_ratings_total",
    "Persisted feedback counts by rating",
    ["rating"],
)
FEEDBACK_AVERAGE = Gauge(
    "compliance_feedback_average_rating", "Average persisted user feedback rating"
)
_client_windows: dict[str, list[float]] = {}
_limit_lock = Lock()
_provider_probe_lock = Lock()
_provider_probe_state: dict = {"success": None, "at": None, "last_attempt": 0.0}
PROVIDER_PROBE_COOLDOWN_SECONDS = 30


@app.middleware("http")
async def per_client_rate_limit(request: Request, call_next):
    started = monotonic()
    supplied = request.headers.get("x-correlation-id", "")
    request.state.correlation_id = (
        supplied if re.fullmatch(r"[A-Za-z0-9-]{1,36}", supplied) else str(uuid.uuid4())
    )
    if request.url.path.endswith("/compliance/requests") and request.method == "POST":
        try:
            maximum = int(settings.api_rate_limit.split("/")[0])
        except (ValueError, IndexError):
            maximum = 60
        client = request.client.host if request.client else "unknown"
        now = monotonic()
        with _limit_lock:
            recent = [t for t in _client_windows.get(client, []) if now - t < 60]
            if len(recent) >= maximum:
                response = JSONResponse(
                    {
                        "detail": "Client request rate limit exceeded.",
                        "correlation_id": request.state.correlation_id,
                    },
                    status_code=429,
                )
                response.headers["X-Correlation-ID"] = request.state.correlation_id
                return response
            recent.append(now)
            _client_windows[client] = recent
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", request.url.path)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    elapsed = monotonic() - started
    API_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    API_LATENCY.labels(request.method, route).observe(elapsed)
    logger.info(
        json.dumps(
            {
                "event": "api_request",
                "correlation_id": request.state.correlation_id,
                "method": request.method,
                "route": route,
                "status_code": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
            }
        )
    )
    return response


@app.exception_handler(RequestValidationError)
async def quarantine_invalid_request(request: Request, exc: RequestValidationError):
    raw = await request.body()
    errors = [
        {
            "field": ".".join(str(x) for x in item.get("loc", [])),
            "code": item.get("type", "validation_error"),
            "message": item.get("msg", "Invalid value"),
        }
        for item in exc.errors()
    ]
    item = QuarantinedRequest(
        id=str(uuid.uuid4()),
        reason="Request schema validation failed",
        payload_digest=hashlib.sha256(raw).hexdigest(),
        field_errors=errors,
    )
    with SessionLocal() as db:
        db.add(item)
        db.commit()
    REQUESTS.labels("quarantined").inc()
    return JSONResponse(
        {"detail": errors, "quarantined": True, "quarantine_id": item.id},
        status_code=422,
    )


def classify(q: str, declared: Domain | None) -> str:
    if declared:
        return declared.value
    s = q.casefold()
    if any(x in s for x in ("gratuity", "fixed-term", "fixed term")):
        return "GRATUITY"
    if any(x in s for x in ("maternity", "pregnan")):
        return "MATERNITY_BENEFIT"
    if any(x in s for x in ("harassment", "posh", "sexual misconduct")):
        return "WORKPLACE_HARASSMENT"
    return "OTHER"


def safe_facts(data: ComplianceInput):
    return {
        k: v.isoformat() if hasattr(v, "isoformat") else v
        for k, v in data.model_dump(exclude={"question", "idempotency_key"}).items()
        if v is not None
    }


def corpus_has_active_statute() -> bool:
    root = Path(settings.corpus_dir) / "ingested"
    for path in root.glob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if (
                    row.get("legal_status") == "ACTIVE"
                    and row.get("provision_type") in {"ACT", "STATUTE", "SECTION"}
                    and row.get("exact_text", "").strip()
                ):
                    return True
        except (OSError, json.JSONDecodeError):
            continue
    return False


@app.get("/api/v1/health", response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "corpus": "not independently verified",
    }


@app.get("/api/v1/ready", response_model=ReadinessResponse)
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "database unavailable") from exc
    corpus_ready = corpus_has_active_statute()
    return {
        "status": "ready",
        "legal_corpus_ready": corpus_ready,
        "mode": "advisory-enabled" if corpus_ready else "fail-closed",
    }


@app.get("/api/v1/evaluations/latest")
def latest_evaluation():
    report = Path(__file__).resolve().parents[1] / "docs" / "evaluation-results.json"
    try:
        return json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            404, "No machine-readable evaluation report is available"
        ) from exc


@app.get("/api/v1/feedback/summary", response_model=FeedbackSummaryResponse)
def feedback_summary(db: Session = Depends(get_db)):
    counts = {
        str(rating): count
        for rating, count in db.query(Feedback.rating, func.count())
        .group_by(Feedback.rating)
        .all()
    }
    total = sum(counts.values())
    average = db.query(func.avg(Feedback.rating)).scalar()
    return {"count": total, "average_rating": average, "rating_counts": counts}


@app.get("/api/v1/settings", response_model=RuntimeSettingsResponse)
def runtime_settings():
    # Expose non-secret runtime settings only; never return connection strings or keys.
    return {
        "app_env": settings.app_env,
        "provider": settings.llm_provider,
        "model": settings.google_model or None,
        "prompt_version": settings.prompt_version,
        "langsmith_tracing": settings.langchain_tracing_v2,
        "otel_exporter_configured": bool(settings.otel_exporter_otlp_endpoint),
        "database_backend": engine.dialect.name,
        "embedding_model_configured": bool(settings.embedding_model),
    }


@app.get("/api/v1/provider/health", response_model=ProviderHealthResponse)
def provider_health():
    return {
        "provider": settings.llm_provider,
        "model": settings.google_model or None,
        "mock_mode_active": settings.llm_provider == "mock",
        "tracing_enabled": settings.langchain_tracing_v2,
        "tracing_project": settings.langchain_project,
        "langsmith_key_configured": bool(settings.langchain_api_key),
        "last_probe_success": _provider_probe_state["success"],
        "last_probe_at": _provider_probe_state["at"],
    }


@app.post("/api/v1/provider/check", response_model=ProviderProbeResponse)
def provider_check():
    """Make one bounded provider request; response and logs never include secrets."""
    settings.validate_provider()
    now = monotonic()
    with _provider_probe_lock:
        remaining = PROVIDER_PROBE_COOLDOWN_SECONDS - (
            now - _provider_probe_state["last_attempt"]
        )
        if remaining > 0:
            raise HTTPException(
                429,
                detail=f"Provider probe is rate limited; retry in {int(remaining) + 1}s.",
                headers={"Retry-After": str(int(remaining) + 1)},
            )
        _provider_probe_state["last_attempt"] = now
    checked_at = datetime.now(UTC)
    try:
        reply = get_provider().invoke(
            "Reply with exactly: provider connection verified."
        )
    except Exception as exc:  # noqa: BLE001 - redact provider SDK messages
        _provider_probe_state.update(success=False, at=checked_at)
        root_error = exc
        while root_error.__cause__ is not None:
            root_error = root_error.__cause__
        response = getattr(root_error, "response", None)
        status_code = getattr(response, "status_code", None)
        provider_code = getattr(root_error, "code", None)
        if callable(provider_code):
            try:
                provider_code = provider_code()
            except Exception:  # noqa: BLE001 - only expose a bounded error code
                provider_code = None
        failure_code = getattr(provider_code, "name", None)
        if failure_code is None and provider_code is not None:
            if isinstance(provider_code, (str, int)):
                failure_code = str(provider_code)
            else:
                failure_code = type(provider_code).__name__
        if status_code is None and isinstance(provider_code, int):
            status_code = provider_code
        if not isinstance(status_code, int):
            status_code = None
        logger.warning(
            json.dumps(
                {
                    "event": "provider_probe_failed",
                    "provider": settings.llm_provider,
                    "error_type": type(root_error).__name__,
                    "provider_code": failure_code,
                    "status_code": status_code,
                }
            )
        )
        raise HTTPException(
            503,
            detail={
                "status": "failed",
                "provider": settings.llm_provider,
                "model": settings.google_model or None,
                "failure_type": type(root_error).__name__,
                "failure_code": failure_code,
                "failure_status_code": status_code,
                "message": "Provider request failed. Check server configuration and provider availability.",
            },
        ) from None
    _provider_probe_state.update(success=True, at=checked_at)
    return {
        "provider": reply.provider,
        "model": reply.model,
        "status": "mock" if reply.provider == "mock" else "connected",
        "connection_attempted": reply.provider != "mock",
        "last_request_succeeded": True,
        "response_received": bool(reply.text.strip()),
        "prompt_tokens": reply.prompt_tokens,
        "completion_tokens": reply.completion_tokens,
    }


@app.get("/api/v1/metrics")
def metrics():
    # Worker processes persist events to the shared DB; deriving gauges from that
    # durable store lets the API scrape endpoint include worker outcomes too.
    RUNS_BY_STATUS.clear()
    RUNS_BY_DECISION.clear()
    AGENT_EVENT_COUNT.clear()
    AGENT_EVENT_LATENCY.clear()
    FEEDBACK_RATINGS.clear()
    with SessionLocal() as db:
        for status, count in (
            db.query(ComplianceRun.status, func.count())
            .group_by(ComplianceRun.status)
            .all()
        ):
            RUNS_BY_STATUS.labels(status).set(count)
        for decision, count in (
            db.query(ComplianceRun.decision, func.count())
            .group_by(ComplianceRun.decision)
            .all()
        ):
            RUNS_BY_DECISION.labels(decision).set(count)
        for agent, event, count in (
            db.query(
                AgentExecution.agent,
                AgentExecution.event,
                func.count(),
            )
            .group_by(AgentExecution.agent, AgentExecution.event)
            .all()
        ):
            AGENT_EVENT_COUNT.labels(agent, event).set(count)
        durations = defaultdict(list)
        for agent, event, value in db.query(
            AgentExecution.agent, AgentExecution.event, AgentExecution.elapsed_ms
        ).all():
            durations[(agent, event)].append(value or 0.0)
        for (agent, event), values in durations.items():
            ordered = sorted(values)
            for quantile in (0.5, 0.95):
                index = max(
                    0, min(len(ordered) - 1, int((len(ordered) - 1) * quantile))
                )
                AGENT_EVENT_LATENCY.labels(agent, event, str(quantile)).set(
                    ordered[index]
                )
        for rating, count in (
            db.query(Feedback.rating, func.count()).group_by(Feedback.rating).all()
        ):
            FEEDBACK_RATINGS.labels(str(rating)).set(count)
        FEEDBACK_AVERAGE.set(db.query(func.avg(Feedback.rating)).scalar() or 0.0)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/compliance/requests", status_code=202, response_model=SubmitResponse)
def submit(data: ComplianceInput, request: Request, db: Session = Depends(get_db)):
    q = data.question
    # Check every user-controlled free-text field before any workflow/LLM call.
    # Quarantine stores a digest and field names, never the sensitive values.
    text_fields = {
        "question": q,
        "establishment_type": data.establishment_type,
        "contract_type": data.contract_type,
    }
    flags = [
        f"{field}:{flag}"
        for field, value in text_fields.items()
        if value
        for flag in inspect_input(value)
    ]
    if flags:
        qid = str(uuid.uuid4())
        payload = json.dumps(
            data.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()
        field_errors = [
            {
                "field": item.split(":", 1)[0],
                "code": item.split(":", 1)[1],
                "message": "Input quarantined before agent execution.",
            }
            for item in flags
        ]
        db.add(
            QuarantinedRequest(
                id=qid,
                reason=", ".join(flags),
                payload_digest=digest,
                field_errors=field_errors,
            )
        )
        db.commit()
        REQUESTS.labels("quarantined").inc()
        raise HTTPException(
            422,
            detail={
                "code": "QUARANTINED",
                "quarantine_id": qid,
                "message": "Request quarantined before agent execution.",
            },
        )
    if data.idempotency_key:
        idempotency_token = hashlib.sha256(data.idempotency_key.encode()).hexdigest()[
            :36
        ]
        existing = (
            db.query(ComplianceRun)
            .filter(ComplianceRun.correlation_id == idempotency_token)
            .first()
        )
        if existing:
            return {
                "run_id": existing.id,
                "status": existing.status,
                "decision": existing.decision,
                "idempotent_replay": True,
            }
    domain = classify(q, data.domain)
    rid = str(uuid.uuid4())
    reqid = str(uuid.uuid4())
    db.add(
        ComplianceRequest(id=reqid, question=q, domain=domain, facts=safe_facts(data))
    )
    request_correlation = request.state.correlation_id
    if data.idempotency_key:
        request_correlation = idempotency_token
    run = ComplianceRun(
        id=rid,
        request_id=reqid,
        status="QUEUED",
        decision="LEGAL_COUNSEL_REVIEW",
        result={},
        prompt_version=settings.prompt_version,
        correlation_id=request_correlation,
    )
    db.add(run)
    db.commit()
    REQUESTS.labels("accepted").inc()
    try:
        if settings.app_env == "production":
            process_run.delay(rid, q, safe_facts(data))
        else:
            # Local dev uses an in-process background thread, never blocks response on retrieval.
            import threading

            from backend.workers.tasks import execute_run

            threading.Thread(
                target=execute_run, args=(rid, q, safe_facts(data)), daemon=True
            ).start()
    except Exception as e:
        run.status = "FAILED"
        run.result = {"error": "Queue unavailable; no advisory was generated."}
        db.commit()
        raise HTTPException(503, "background execution unavailable") from e
    return {
        "run_id": rid,
        "status": "QUEUED",
        "domain": domain,
        "correlation_id": run.correlation_id,
        "provider": settings.llm_provider,
    }


@app.get("/api/v1/compliance/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(ComplianceRun, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return {
        "run_id": run.id,
        "status": run.status,
        "decision": run.decision,
        "prompt_version": run.prompt_version,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "result": run.result,
    }


@app.get("/api/v1/compliance/runs", response_model=RunHistoryResponse)
def list_runs(
    limit: int = Query(default=25, ge=1, le=100), db: Session = Depends(get_db)
):
    rows = (
        db.query(ComplianceRun)
        .order_by(ComplianceRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [
            {
                "run_id": row.id,
                "status": row.status,
                "decision": row.decision,
                "prompt_version": row.prompt_version,
                "created_at": row.created_at,
                "completed_at": row.completed_at,
            }
            for row in rows
        ]
    }


@app.get("/api/v1/compliance/runs/{run_id}/status", response_model=RunStatusResponse)
def get_status(run_id: str, db: Session = Depends(get_db)):
    run = db.get(ComplianceRun, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return {"run_id": run.id, "status": run.status, "decision": run.decision}


@app.get("/api/v1/compliance/runs/{run_id}/trace", response_model=TraceResponse)
def get_trace(run_id: str, db: Session = Depends(get_db)):
    if not db.get(ComplianceRun, run_id):
        raise HTTPException(404, "run not found")
    events = (
        db.query(AgentExecution)
        .filter(AgentExecution.run_id == run_id)
        .order_by(AgentExecution.id)
        .all()
    )
    return {
        "run_id": run_id,
        "events": [
            {
                "agent": e.agent,
                "event": e.event,
                "detail": e.detail,
                "elapsed_ms": e.elapsed_ms,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }


@app.post(
    "/api/v1/compliance/feedback", status_code=201, response_model=FeedbackResponse
)
def feedback(data: FeedbackInput, db: Session = Depends(get_db)):
    if not db.get(ComplianceRun, data.run_id):
        raise HTTPException(404, "run not found")
    item = Feedback(
        id=str(uuid.uuid4()),
        run_id=data.run_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(item)
    db.commit()
    return {"id": item.id, "accepted": True}


@app.exception_handler(Exception)
async def safe_errors(request: Request, exc: Exception):
    # Keep provider failures and prompts out of response/log body.
    logger.error(
        json.dumps(
            {
                "event": "unhandled_api_error",
                "correlation_id": getattr(request.state, "correlation_id", None),
                "error_type": type(exc).__name__,
            }
        )
    )
    return Response(
        content=json.dumps(
            {"detail": "Internal error; no verified advisory was produced."}
        ),
        status_code=500,
        media_type="application/json",
    )
