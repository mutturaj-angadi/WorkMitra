import json
import logging
from datetime import UTC, datetime

from backend.config import configure_langchain_tracing, get_settings
from backend.database import SessionLocal
from backend.llm.provider import get_provider
from backend.models import AgentExecution, ComplianceRun
from backend.orchestrator.graph import run_advisory
from backend.workers.celery_app import celery_app

logger = logging.getLogger("compliance_desk.worker")


def execute_run(run_id: str, question: str, request: dict):
    configure_langchain_tracing()
    db = SessionLocal()
    try:
        run = db.get(ComplianceRun, run_id)
        if not run or run.status == "COMPLETED":
            return
        run.status = "RUNNING"
        db.commit()
        db.add(
            AgentExecution(
                run_id=run_id,
                agent="orchestrator",
                event="run_started",
                detail={
                    "correlation_id": run.correlation_id,
                    "prompt_version": run.prompt_version,
                },
            )
        )
        db.commit()
        if get_settings().llm_provider == "stub":
            get_provider().invoke("latency measurement only")
        result = run_advisory(question, request)
        run.result = result
        run.decision = result["decision"]
        run.status = "COMPLETED"
        run.completed_at = datetime.now(UTC)
        node_agents = {
            "research": "research-agent",
            "retry_research": "research-agent",
            "verification": "verification-agent",
            "verify_retry": "verification-agent",
        }
        for event in result.get("trace", []):
            db.add(
                AgentExecution(
                    run_id=run_id,
                    agent=node_agents.get(event.get("node"), "orchestrator"),
                    event=event.get("node", "workflow_event"),
                    detail={
                        **event.get("detail", {}),
                        "started_at": event.get("started_at"),
                        "completed_at": event.get("completed_at"),
                        "correlation_id": run.correlation_id,
                        "prompt_version": run.prompt_version,
                    },
                    elapsed_ms=event.get("elapsed_ms", 0),
                )
            )
        for call in result["tool_calls"]:
            db.add(
                AgentExecution(
                    run_id=run_id,
                    agent="research-agent",
                    event="tool_call",
                    detail={
                        **call,
                        "correlation_id": run.correlation_id,
                        "prompt_version": run.prompt_version,
                    },
                    elapsed_ms=call.get("latency_ms", 0),
                )
            )
        for agent, event, detail in [
            (
                "research-agent",
                "retrieval_complete",
                {"tool_calls": result["tool_calls"], "passages": result["evidence"]},
            ),
            (
                "verification-agent",
                result["verification"]["status"],
                result["verification"],
            ),
            (
                "orchestrator",
                "run_completed",
                {"decision": result["decision"], "retry_count": result["retry_count"]},
            ),
        ]:
            db.add(
                AgentExecution(
                    run_id=run_id,
                    agent=agent,
                    event=event,
                    detail={
                        **detail,
                        "correlation_id": run.correlation_id,
                        "prompt_version": run.prompt_version,
                    },
                )
            )
        db.commit()
        logger.info(
            json.dumps(
                {
                    "event": "run_completed",
                    "run_id": run_id,
                    "correlation_id": run.correlation_id,
                    "status": run.status,
                    "decision": run.decision,
                    "retry_count": result["retry_count"],
                }
            )
        )
        return {"run_id": run_id, "status": run.status, "decision": run.decision}
    except Exception as exc:
        run = db.get(ComplianceRun, run_id)
        if run:
            run.status = "FAILED"
            run.decision = "LEGAL_COUNSEL_REVIEW"
            run.result = {
                "decision": "LEGAL_COUNSEL_REVIEW",
                "advisory": "The workflow did not complete; no verified result was produced.",
                "escalation_reason": "Background execution failed.",
                "verification": {
                    "status": "ESCALATE",
                    "verified": False,
                    "reasons": ["Background execution failed safely."],
                    "citations": [],
                    "excluded": [],
                },
                "evidence": [],
                "tool_calls": [],
                "retry_count": 0,
            }
            run.completed_at = datetime.now(UTC)
            db.add(
                AgentExecution(
                    run_id=run_id,
                    agent="orchestrator",
                    event="run_failed",
                    detail={
                        "error_type": type(exc).__name__,
                        "correlation_id": run.correlation_id,
                        "prompt_version": run.prompt_version,
                    },
                )
            )
            db.commit()
            logger.error(
                json.dumps(
                    {
                        "event": "background_run_failed",
                        "run_id": run_id,
                        "correlation_id": run.correlation_id,
                        "error_type": type(exc).__name__,
                    }
                )
            )
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def process_run(self, run_id: str, question: str, request: dict):
    return execute_run(run_id, question, request)
