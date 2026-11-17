from datetime import date

from backend.agents.research import ResearchAgent
from backend.agents.verification import VerificationAgent
from backend.orchestrator.graph import run_advisory
from backend.rag.chunking import split_sections
from backend.rag.metadata import validate_metadata
from backend.rag.retriever import CorpusRetriever


def test_empty_corpus_fails_closed():
    result = run_advisory(
        "Is gratuity payable after a fixed-term contract?",
        {},
        research=ResearchAgent(CorpusRetriever("backend/tests/fixtures/empty")),
    )
    assert result["decision"] == "LEGAL_COUNSEL_REVIEW"
    assert result["verification"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["retry_count"] == 1


def test_official_faq_alone_does_not_verify_statute():
    result = run_advisory(
        "Fixed term gratuity after 18 months?",
        {},
        research=ResearchAgent(CorpusRetriever("corpus")),
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


def test_langgraph_traces_gates_tools_and_retry():
    result = run_advisory(
        "Is gratuity payable after a fixed-term contract of 18 months?",
        {},
        research=ResearchAgent(CorpusRetriever("backend/tests/fixtures/empty")),
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


def test_verifier_applies_relevant_date_and_citation_ids():
    passage = {
        "text": "Section 53 exact official words",
        "metadata": {
            "chunk_id": "css-53-a",
            "document_id": "css",
            "statute_name": "Code on Social Security, 2020",
            "section": "53",
            "subsection": "1",
            "clause": "second proviso",
            "provision_type": "SECTION",
            "legal_status": "ACTIVE",
            "effective_from": "2025-11-21",
            "effective_to": None,
            "source_url": "https://www.indiacode.nic.in/example.pdf",
            "source_version": "Act 36 of 2020 text as on 2025-11-21",
            "page_number": 42,
        },
    }
    verifier = VerificationAgent()
    assert not verifier.verify([passage], relevant_date=date(2025, 11, 20))["verified"]
    current = verifier.verify([passage], relevant_date=date(2025, 11, 22))
    assert (
        current["verified"]
        and current["citations"][0]["chunk_id"] == passage["metadata"]["chunk_id"]
    )
