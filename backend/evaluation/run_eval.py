"""Run deterministic routing/retrieval checks; this does not score generated answers."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from backend.agents.research import ResearchAgent
from backend.guardrails import inspect_input
from backend.orchestrator.graph import run_advisory
from backend.rag.retriever import CorpusRetriever
from backend.schemas import ComplianceInput

SAFE_NONANSWER = {
    "LEGAL_COUNSEL_REVIEW",
    "REQUEST_MORE_ESTABLISHMENT_DETAIL",
    "QUARANTINED",
    "INVALID",
}


def evaluate(rows, corpus="corpus"):
    # Evaluation remains deterministic when the developer .env enables Gemini.
    research = ResearchAgent(CorpusRetriever(corpus), use_model_planner=False)
    outcomes = []
    for row in rows:
        question = row["question"]
        actual = {
            "decision": "LEGAL_COUNSEL_REVIEW",
            "evidence": [],
            "verification": {"verified": False, "status": "INSUFFICIENT_EVIDENCE"},
            "retry_count": 0,
        }
        started = perf_counter()
        flags = inspect_input(question)
        if "prompt_injection" in flags or "possible_sensitive_identifier" in flags:
            actual["decision"] = "QUARANTINED"
        else:
            try:
                ComplianceInput.model_validate(
                    {"question": question, "domain": row.get("input_domain")}
                )
            except ValidationError:
                actual["decision"] = "INVALID"
            else:
                actual = run_advisory(
                    question,
                    {"domain": row.get("input_domain")},
                    research=research,
                    trace_enabled=False,
                )
        elapsed = (perf_counter() - started) * 1000
        evidence = actual.get("evidence", [])
        query_terms = {
            t.casefold().strip(".,?!:;()\"'") for t in question.split() if len(t) > 2
        }
        relevance = []
        for passage in evidence:
            words = set(passage.get("text", "").casefold().split())
            relevance.append(
                len(query_terms & words) / len(query_terms) if query_terms else 0.0
            )
        expected_passage = row.get("supporting_passage", "")
        passage_found = (
            any(
                expected_passage.casefold() in p.get("text", "").casefold()
                for p in evidence
            )
            if expected_passage
            else None
        )
        expected_statute = row.get("expected_statute")
        expected_section = row.get("expected_section")
        eligible = [
            p
            for p in evidence
            if expected_statute
            and expected_section
            and expected_statute.casefold()
            in p.get("metadata", {}).get("statute_name", "").casefold()
            and expected_section.split(",")[0].casefold()
            in p.get("metadata", {}).get("section", "").casefold()
        ]
        retrieved_precision = len(eligible) / len(evidence) if evidence else 0.0
        citation_ids = {
            c.get("chunk_id")
            for c in actual.get("verification", {}).get("citations", [])
        }
        evidence_by_id = {p.get("metadata", {}).get("chunk_id"): p for p in evidence}
        citation_correct = bool(citation_ids) and citation_ids.issubset(evidence_by_id)
        outcomes.append(
            {
                "scenario_id": row["scenario_id"],
                "expected": row["expected_outcome"],
                "actual": actual["decision"],
                "expected_domain": row.get("expected_domain"),
                "actual_domain": actual.get("domain"),
                "classification_evaluable": actual.get("domain") is not None,
                "classification_correct": actual.get("domain")
                == row.get("expected_domain")
                if actual.get("domain") is not None
                else None,
                "correct": actual["decision"] == row["expected_outcome"],
                "verification": actual.get("verification", {}).get("status"),
                "evidence_count": len(evidence),
                "expected_passage_retrieved": passage_found,
                "expected_statute_section_retrieved": bool(eligible)
                if expected_statute and expected_section
                else None,
                "retrieval_precision_at_k": retrieved_precision
                if expected_statute and expected_section
                else None,
                "context_relevance": sum(relevance) / len(relevance)
                if relevance
                else 0.0,
                "citation_correctness": citation_correct
                if actual.get("decision") == "ANSWER_WITH_CITATION"
                else None,
                "citation_completeness": None,
                "retry_count": actual.get("retry_count", 0),
                "latency_ms": round(elapsed, 2),
            }
        )
    total = len(outcomes)
    answered = [o for o in outcomes if o["actual"] == "ANSWER_WITH_CITATION"]
    citation_evaluable = [
        o
        for o in outcomes
        if o["expected_passage_retrieved"] is not None
        and o.get("expected_statute_section_retrieved") is not None
    ]
    supported = sum(bool(o["citation_correctness"]) for o in answered)
    denom = len(answered)
    means = lambda key, items: (
        sum(o[key] for o in items) / len(items) if items else None
    )
    return {
        "sample_count": total,
        "evaluation_type": "deterministic safety-routing and retrieval; no answer generation",
        "outcome_accuracy": sum(o["correct"] for o in outcomes) / total
        if total
        else 0.0,
        "classification_accuracy": means(
            "classification_correct",
            [o for o in outcomes if o["classification_correct"] is not None],
        ),
        "classification_sample_count": sum(
            o["classification_evaluable"] for o in outcomes
        ),
        "escalation_correctness": sum(
            o["correct"] for o in outcomes if o["expected"] == "LEGAL_COUNSEL_REVIEW"
        )
        / sum(o["expected"] == "LEGAL_COUNSEL_REVIEW" for o in outcomes)
        if any(o["expected"] == "LEGAL_COUNSEL_REVIEW" for o in outcomes)
        else None,
        "clarification_correctness": sum(
            o["correct"]
            for o in outcomes
            if o["expected"] == "REQUEST_MORE_ESTABLISHMENT_DETAIL"
        )
        / sum(o["expected"] == "REQUEST_MORE_ESTABLISHMENT_DETAIL" for o in outcomes)
        if any(o["expected"] == "REQUEST_MORE_ESTABLISHMENT_DETAIL" for o in outcomes)
        else None,
        "retrieval_precision_at_k": means(
            "retrieval_precision_at_k",
            [o for o in outcomes if o["retrieval_precision_at_k"] is not None],
        ),
        "retrieval_recall_at_k": sum(
            bool(o["expected_passage_retrieved"]) for o in citation_evaluable
        )
        / len(citation_evaluable)
        if citation_evaluable
        else None,
        "citation_correctness": supported / denom if denom else None,
        "citation_completeness": None,
        "groundedness": supported / denom if denom else None,
        "context_relevance": means("context_relevance", outcomes),
        "faithfulness": None,
        "unsupported_claim_rate": None,
        "hallucination_rate": None,
        "answer_run_denominator": denom,
        "safe_abstention_rate": sum(
            o["actual"] in SAFE_NONANSWER and o["expected"] in SAFE_NONANSWER
            for o in outcomes
        )
        / sum(o["expected"] in SAFE_NONANSWER for o in outcomes)
        if any(o["expected"] in SAFE_NONANSWER for o in outcomes)
        else None,
        "latency_ms": {
            "mean": means("latency_ms", outcomes),
            "max": max((o["latency_ms"] for o in outcomes), default=None),
        },
        "details": outcomes,
        "metric_definitions": {
            "groundedness": "Verified citation-bearing runs with all cited chunk IDs present in that run's retrieved passages / citation-bearing runs; null when none.",
            "context_relevance": "Per scenario, mean lexical overlap of query tokens with retrieved passage tokens; no passages score zero.",
            "faithfulness": "Not measured: no claim generation or human claim-entailment annotation.",
            "hallucination_rate": "Not measured: no answer runs. A zero would be misleading, so this metric is null.",
            "retrieval_precision_at_k": "Relevant retrieved passages (matching labeled statute and section) / all retrieved passages for cases with labels.",
            "retrieval_recall_at_k": "Cases with the labeled supporting passage retrieved / cases with an explicit supporting-passage label.",
            "citation_correctness": "Verified citation identifiers that resolve to retrieved evidence / answer runs.",
            "citation_completeness": "Not measured: no generated claims to map to citations.",
        },
        "limitation": "Routing and classification are measured separately. No answer-generation metrics are inferred from routing scores. The primary Code on Social Security text is not indexed; the 18-month fixed-term oracle must fail closed.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="backend/evaluation/scenarios.json")
    parser.add_argument("--corpus", default="corpus")
    parser.add_argument("--output", default="docs/evaluation-results.json")
    args = parser.parse_args()
    rows = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))
    report = evaluate(rows, args.corpus)
    report["generated_at"] = datetime.now(UTC).isoformat()
    report["prompt_comparison"] = {
        "measured": False,
        "reason": "The current safety-routing workflow does not call a generative model; v1/v2 prompt artifacts therefore cannot be compared as answer quality.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, indent=2))
    print(f"Machine-readable results: {out}")


if __name__ == "__main__":
    main()
