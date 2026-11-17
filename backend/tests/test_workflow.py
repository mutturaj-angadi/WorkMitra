from datetime import date

from backend.agents.research import ResearchAgent
from backend.agents.verification import VerificationAgent
from backend.orchestrator.graph import run_advisory
from backend.rag.chunking import split_sections
from backend.rag.metadata import validate_metadata
from backend.rag.retriever import CorpusRetriever


def test_empty_corpus_fails_closed(empty_test_corpus):
    result = run_advisory(
        "Is gratuity payable after a fixed-term contract?",
        {},
        research=ResearchAgent(CorpusRetriever(empty_test_corpus)),
    )
    assert result["decision"] == "LEGAL_COUNSEL_REVIEW"
    assert result["verification"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["retry_count"] == 1


def test_gazette_commencement_notice_alone_does_not_verify_gratuity(
    gazette_test_corpus,
):
    result = run_advisory(
        "Fixed term gratuity after 18 months?",
        {
            "contract_type": "direct fixed-term",
            "contract_written": True,
            "contract_duration_months": 18,
            "employment_start": "2025-11-22",
            "employment_end": "2027-05-21",
        },
        research=ResearchAgent(CorpusRetriever(gazette_test_corpus)),
    )
    assert result["decision"] == "LEGAL_COUNSEL_REVIEW"
    assert result["verification"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_verifier_rejects_repealed_and_unknown_status():
    passage = {
        "text": "Exact copied passage",
        "metadata": {
            "legal_status": "REPEALED",
            "source_url": "https://example.invalid",
            "source_version": "1",
        },
    }
    assert VerificationAgent().verify([passage])["verified"] is False


def test_section_chunking_keeps_source_text():
    out = split_sections(
        "Section 1. Intro\nExact statutory words\n\nSection 2. Scope\nOther text"
    )
    assert len(out) >= 2 and "Exact statutory words" in out[0].text


def test_chunking_overlap_is_configurable_and_validated():
    chunks = split_sections("x" * 25, max_chars=10, overlap_chars=3)
    assert chunks[0].text[-3:] == chunks[1].text[:3]
    try:
        split_sections("x", max_chars=10, overlap_chars=10)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid overlap should fail")


def test_metadata_rejects_missing_fields():
    try:
        validate_metadata({})
    except ValueError as e:
        assert "Missing corpus metadata" in str(e)
    else:
        raise AssertionError("expected metadata error")


def test_langgraph_traces_gates_tools_and_retry(empty_test_corpus):
    result = run_advisory(
        "Is gratuity payable after a fixed-term contract of 18 months?",
        {},
        research=ResearchAgent(CorpusRetriever(empty_test_corpus)),
    )
    assert [event["node"] for event in result["trace"]] == [
        "classify",
        "fact_check",
        "human_review_gate",
        "research",
        "verification",
        "retry_research",
        "verification",
        "decision",
    ]
    assert result["retry_count"] == 1
    assert len(result["tool_calls"]) <= 8
    assert all(
        event["elapsed_ms"] >= 0 and event["completed_at"] for event in result["trace"]
    )


def test_verifier_applies_relevant_date_and_returns_fixture_citation(
    gazette_test_corpus,
):
    passages = CorpusRetriever(gazette_test_corpus).search_corpus(
        "section 53 sections 17 to 141 21st November 2025 commencement",
        document_ids=("so-5319-e-2025",),
    )
    verifier = VerificationAgent()
    assert not verifier.verify(
        passages,
        relevant_date=date(2025, 11, 20),
        question="When did Section 53 come into force?",
    )["verified"]
    current = verifier.verify(
        passages,
        relevant_date=date(2025, 11, 21),
        question="When did Section 53 come into force?",
    )
    assert current["verified"] and current["citations"][0]["chunk_id"] in {
        passage["metadata"]["chunk_id"] for passage in passages
    }
