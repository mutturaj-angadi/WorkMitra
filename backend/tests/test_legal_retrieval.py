import json
import tempfile
from datetime import date
from hashlib import sha256
from pathlib import Path

from backend.agents.research import ResearchAgent
from backend.orchestrator.graph import run_advisory
from backend.rag.retriever import CorpusRetriever


def _row(document_id, legal_status, effective_from, effective_to, text):
    return {
        "document_id": document_id,
        "statute_name": document_id,
        "section": "4",
        "subsection": "",
        "clause": "",
        "provision_type": "ACT",
        "legal_status": legal_status,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "source_url": "https://example.invalid/source.pdf",
        "source_version": "test fixture",
        "page_number": 1,
        "chunk_id": document_id,
        "exact_text": text,
        "checksum": sha256(text.encode()).hexdigest(),
    }


def test_current_law_filter_excludes_repealed_and_honors_historical_date():
    with tempfile.TemporaryDirectory(
        prefix="retrieval-test-", dir="backend/tests"
    ) as root:
        corpus = Path(root) / "corpus"
        out = corpus / "ingested"
        out.mkdir(parents=True)
        rows = [
            _row("current-code", "ACTIVE", "2025-11-21", None, "gratuity provision"),
            _row(
                "historical-act",
                "REPEALED",
                "1972-09-16",
                "2025-11-20",
                "gratuity provision",
            ),
        ]
        (out / "sources.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )
        retriever = CorpusRetriever(corpus)
        current = retriever.search_corpus("gratuity provision")
        assert [row["metadata"]["document_id"] for row in current] == ["current-code"]
        historical = retriever.search_corpus(
            "gratuity provision",
            as_of_date=date(2025, 11, 20),
            include_historical=True,
        )
        assert [row["metadata"]["document_id"] for row in historical] == [
            "historical-act"
        ]


def test_retrieval_normalizes_punctuation_and_preserves_chunk_checksum():
    with tempfile.TemporaryDirectory(
        prefix="retrieval-test-", dir="backend/tests"
    ) as root:
        corpus = Path(root) / "corpus"
        out = corpus / "ingested"
        out.mkdir(parents=True)
        source = _row(
            "gazette",
            "ACTIVE",
            "2025-11-21",
            None,
            "Sections 17 to 141; commencement on 21st November, 2025.",
        )
        (out / "gazette.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
        rows = CorpusRetriever(corpus).search_corpus("sections 17 to 141; 2025")
        assert rows and rows[0]["metadata"]["checksum"] == source["checksum"]


def test_official_gazette_supports_commencement_answer_for_section_53():
    result = run_advisory(
        "When did Section 53 come into force?",
        {"domain": "OTHER"},
        research=ResearchAgent(CorpusRetriever("corpus")),
    )
    assert result["decision"] == "ANSWER_WITH_CITATION"
    assert "2025-11-21" in result["advisory"]
    assert any(
        item.get("document_id") == "so-5319-e-2025"
        for item in result["verification"]["citations"]
    )
