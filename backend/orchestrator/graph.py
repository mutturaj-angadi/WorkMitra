"""Executable, bounded LangGraph workflow for evidence-based HR triage."""

import re
from datetime import UTC, date, datetime, timedelta
from time import perf_counter
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.research import ResearchAgent
from backend.agents.verification import VerificationAgent


class WorkflowState(TypedDict, total=False):
    question: str
    request: dict
    domain: str
    evidence: list[dict]
    tool_calls: list[dict]
    verification: dict
    retry_count: int
    decision: str
    advisory: str
    escalation_reason: str | None
    trace: list[dict]


def _event(node: str, started: float, detail: dict) -> dict:
    elapsed = perf_counter() - started
    completed = datetime.now(UTC)
    return {
        "node": node,
        "started_at": (completed - timedelta(seconds=elapsed)).isoformat(),
        "completed_at": completed.isoformat(),
        "elapsed_ms": round(elapsed * 1000, 2),
        "detail": detail,
    }


def _classify(question: str, request: dict) -> str:
    if request.get("domain"):
        return str(request["domain"]).upper()
    text = question.casefold()
    if any(term in text for term in ("gratuity", "fixed-term", "fixed term")):
        return "GRATUITY"
    if any(term in text for term in ("maternity", "pregnan")):
        return "MATERNITY_BENEFIT"
    if any(term in text for term in ("harassment", "posh", "sexual misconduct")):
        return "WORKPLACE_HARASSMENT"
    return "OTHER"


def build_workflow(research: ResearchAgent, verifier: VerificationAgent):
    """Compile a graph with typed agent handoff, conditional routing and one retry."""
    graph = StateGraph(WorkflowState)

    def classify_node(state: WorkflowState) -> dict:
        started = perf_counter()
        domain = _classify(state["question"], state.get("request", {}))
        trace = list(state.get("trace", []))
        trace.append(_event("classify", started, {"domain": domain}))
        return {"domain": domain, "trace": trace}

    def facts_gate(state: WorkflowState) -> dict:
        started = perf_counter()
        request = state.get("request", {})
        missing = state.get("domain") == "MATERNITY_BENEFIT" and not all(
            request.get(k) is not None for k in ("headcount", "establishment_type")
        )
        trace = list(state.get("trace", []))
        trace.append(
            _event("fact_check", started, {"missing_establishment_details": missing})
        )
        if missing:
            return {
                "decision": "REQUEST_MORE_ESTABLISHMENT_DETAIL",
                "verification": {
                    "status": "REQUIRES_MORE_INFORMATION",
                    "verified": False,
                    "reasons": ["Establishment coverage facts are missing."],
                    "citations": [],
                    "excluded": [],
                },
                "advisory": "Please provide the establishment type and approximate employee headcount so applicability can be checked.",
                "escalation_reason": None,
                "trace": trace,
            }
        return {"trace": trace}

    def harassment_gate(state: WorkflowState) -> dict:
        started = perf_counter()
        question = state["question"].casefold()
        domain = state.get("domain", "")
        termination = any(
            term in question
            for term in (
                "disputes termination",
                "dispute about termination",
                "contest the termination",
                "challenging termination",
            )
        )
        harassment = domain == "WORKPLACE_HARASSMENT" or any(
            term in question
            for term in ("harassment complaint", "sexual harassment", "posh complaint")
        )
        must_escalate = termination or harassment
        trace = list(state.get("trace", []))
        trace.append(
            _event(
                "human_review_gate",
                started,
                {
                    "termination_dispute": termination,
                    "harassment_complaint": harassment,
                },
            )
        )
        if must_escalate:
            reason = (
                "Harassment complaint requires human/committee review."
                if harassment
                else "Termination dispute requires qualified legal review."
            )
            return {
                "decision": "LEGAL_COUNSEL_REVIEW",
                "verification": {
                    "status": "ESCALATE",
                    "verified": False,
                    "reasons": [reason],
                    "citations": [],
                    "excluded": [],
                },
                "advisory": "This matter is routed to qualified human review. Preserve confidentiality and follow the applicable complaint process.",
                "escalation_reason": reason,
                "trace": trace,
            }
        return {"trace": trace}

    def initial_research(state: WorkflowState) -> dict:
        started = perf_counter()
        output = research.run(
            state["question"], state.get("request", {}), strategy="initial"
        )
        trace = list(state.get("trace", []))
        trace.append(
            _event(
                "research",
                started,
                {
                    "strategy": output["strategy"],
                    "tool_calls": output["tool_calls"],
                    "passage_count": len(output["passages"]),
                    "errors": output["errors"],
                },
            )
        )
        return {
            "evidence": output["passages"],
            "tool_calls": output["tool_calls"],
            "trace": trace,
        }

    def verify(state: WorkflowState) -> dict:
        started = perf_counter()
        when = state.get("request", {}).get("employment_end") or state.get(
            "request", {}
        ).get("employment_start")
        if isinstance(when, str):
            try:
                when = date.fromisoformat(when)
            except ValueError:
                when = None
        output = verifier.verify(
            state.get("evidence", []),
            relevant_date=when,
            question=state["question"],
            domain=state.get("domain", ""),
            case_facts=state.get("request", {}),
        )
        trace = list(state.get("trace", []))
        trace.append(
            _event(
                "verification",
                started,
                {
                    "status": output["status"],
                    "verified": output["verified"],
                    "citation_count": len(output.get("citations", [])),
                    "reasons": output["reasons"],
                },
            )
        )
        return {"verification": output, "trace": trace}

    def retry_research(state: WorkflowState) -> dict:
        started = perf_counter()
        question = state["question"]
        derived = (
            f"{question} exceptions modifying provision commencement effective date"
        )
        output = research.run(
            derived, state.get("request", {}), strategy="query-derived-second-search"
        )
        combined = list(state.get("evidence", [])) + output["passages"]
        unique = {
            item.get("metadata", {}).get("chunk_id"): item
            for item in combined
            if item.get("metadata", {}).get("chunk_id")
        }
        trace = list(state.get("trace", []))
        trace.append(
            _event(
                "retry_research",
                started,
                {
                    "strategy": output["strategy"],
                    "tool_calls": output["tool_calls"],
                    "passage_count": len(output["passages"]),
                    "errors": output["errors"],
                    "retry": 1,
                },
            )
        )
        return {
            "evidence": list(unique.values()),
            "tool_calls": list(state.get("tool_calls", [])) + output["tool_calls"],
            "retry_count": 1,
            "trace": trace,
        }

    def decision_node(state: WorkflowState) -> dict:
        started = perf_counter()
        verification = state["verification"]
        verified = bool(verification.get("verified"))
        needs_facts = verification.get("status") == "REQUIRES_MORE_INFORMATION"
        decision = (
            "ANSWER_WITH_CITATION"
            if verified
            else "REQUEST_MORE_ESTABLISHMENT_DETAIL"
            if needs_facts
            else "LEGAL_COUNSEL_REVIEW"
        )
        trace = list(state.get("trace", []))
        trace.append(
            _event(
                "decision",
                started,
                {"decision": decision},
            )
        )
        advisory = (
            "The retrieved official source passage passed source and effective-date checks. Review the linked passage before applying it to a specific case."
            if verified
            else "Please provide the missing contract facts so the applicable rule can be checked."
            if needs_facts
            else "The corpus does not contain sufficient verified official statutory evidence. Please consult qualified legal counsel."
        )
        question = state["question"].casefold()
        if verified and any(
            term in question
            for term in (
                "commencement",
                "commenced",
                "came into force",
                "come into force",
                "effective date",
            )
        ):
            notice_text = " ".join(
                p.get("text", "").casefold()
                for p in state.get("evidence", [])
                if p.get("metadata", {}).get("document_id") == "so-5319-e-2025"
            )
            section_match = re.search(r"\bsection\s*(\d+)\b", question)
            range_match = re.search(r"sections\s+(\d+)\s+to\s+(\d+)", notice_text)
            notice = next(
                (
                    c
                    for c in verification.get("citations", [])
                    if c.get("document_id") == "so-5319-e-2025"
                ),
                {},
            )
            if (
                section_match
                and range_match
                and int(range_match.group(1))
                <= int(section_match.group(1))
                <= int(range_match.group(2))
                and notice.get("effective_from")
            ):
                advisory = (
                    f"The retrieved Gazette notification lists sections {range_match.group(1)} to {range_match.group(2)} "
                    f"for commencement on {notice['effective_from']}. Section {section_match.group(1)} falls within that range."
                )
        return {
            "decision": decision,
            "advisory": advisory,
            "escalation_reason": None
            if verified
            else "Required contract or employment facts are missing."
            if needs_facts
            else "Insufficient or unverified statutory evidence.",
            "trace": trace,
        }

    def direct_or_continue(state: WorkflowState) -> str:
        if state.get("decision"):
            return "finish"
        return "research"

    def after_first_verify(state: WorkflowState) -> str:
        return (
            "decision"
            if state.get("verification", {}).get("verified")
            else "retry_research"
        )

    graph.add_node("classify", classify_node)
    graph.add_node("fact_check", facts_gate)
    graph.add_node("human_review_gate", harassment_gate)
    graph.add_node("research", initial_research)
    graph.add_node("verify", verify)
    graph.add_node("retry_research", retry_research)
    graph.add_node("verify_retry", verify)
    graph.add_node("decision", decision_node)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "fact_check")
    graph.add_conditional_edges(
        "fact_check",
        direct_or_continue,
        {"finish": END, "research": "human_review_gate"},
    )
    graph.add_conditional_edges(
        "human_review_gate", direct_or_continue, {"finish": END, "research": "research"}
    )
    graph.add_edge("research", "verify")
    graph.add_conditional_edges(
        "verify",
        after_first_verify,
        {"decision": "decision", "retry_research": "retry_research"},
    )
    graph.add_edge("retry_research", "verify_retry")
    graph.add_edge("verify_retry", "decision")
    graph.add_edge("decision", END)
    return graph.compile()


def run_advisory(
    question: str,
    request: dict,
    research=None,
    verifier=None,
    trace_enabled: bool | None = None,
) -> dict:
    research = research or ResearchAgent()
    verifier = verifier or VerificationAgent()
    app = build_workflow(research, verifier)
    try:
        state = {
            "question": question,
            "request": request,
            "evidence": [],
            "tool_calls": [],
            "retry_count": 0,
            "trace": [],
        }
        from backend.config import get_settings

        settings = get_settings()
        should_trace = (
            settings.langchain_tracing_v2 if trace_enabled is None else trace_enabled
        )
        if should_trace:
            from langchain_core.tracers.context import tracing_v2_enabled
            from langsmith import Client

            with tracing_v2_enabled(
                project_name=settings.langchain_project,
                client=Client(api_key=settings.langchain_api_key),
            ):
                result = app.invoke(state, config={"recursion_limit": 12})
        else:
            result = app.invoke(state, config={"recursion_limit": 12})
    # Unexpected graph failures must produce a non-answer, never an assertion.
    except Exception as exc:  # noqa: BLE001
        return {
            "decision": "LEGAL_COUNSEL_REVIEW",
            "verification": {
                "status": "ESCALATE",
                "verified": False,
                "reasons": ["Workflow execution failed safely."],
                "citations": [],
                "excluded": [],
            },
            "evidence": [],
            "tool_calls": [],
            "retry_count": 0,
            "trace": [
                {
                    "node": "workflow_error",
                    "completed_at": datetime.now(UTC).isoformat(),
                    "detail": {"error_type": type(exc).__name__},
                }
            ],
            "advisory": "No verified result was produced. Please consult qualified legal counsel.",
            "escalation_reason": "Workflow execution failed safely.",
        }
    return {
        key: result.get(key)
        for key in (
            "decision",
            "verification",
            "evidence",
            "tool_calls",
            "retry_count",
            "trace",
            "advisory",
            "escalation_reason",
            "domain",
        )
    }
