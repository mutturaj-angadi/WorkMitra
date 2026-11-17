import json
import tempfile
from datetime import date
from hashlib import sha256
from pathlib import Path

from backend.agents.research import ResearchAgent
from backend.orchestrator.graph import run_advisory
from backend.rag.metadata import validate_metadata
from backend.rag.retriever import CorpusRetriever


def _row(document_id, legal_status, effective_from, effective_to, text):
    exact_text = f"TEST ONLY; not legal text: {text}"
    return {
        "document_id": document_id,
        "statute_name": f"TEST FIXTURE ONLY (not law): {document_id}",
        "section": "test fixture",
        "subsection": "",
        "clause": "",
        "provision_type": "TEST_FIXTURE",
        "legal_status": legal_status,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "source_url": "https://example.invalid/test-fixture.jsonl",
        "source_version": "synthetic retrieval test data, not a source version",
        "page_number": 1,
        "chunk_id": document_id,
        "exact_text": exact_text,
        "checksum": sha256(exact_text.encode()).hexdigest(),
    }


def test_current_law_filter_excludes_repealed_and_honors_historical_date():
    with tempfile.TemporaryDirectory(
        prefix="retrieval-test-", dir=Path(__file__).resolve().parent
    ) as root:
        corpus = Path(root) / "corpus"
        out = corpus / "ingested"
        out.mkdir(parents=True)
        rows = [
            _row("test-current-source", "ACTIVE", "2025-11-21", None, "token alpha"),
            _row(
                "test-historical-source",
                "REPEALED",
                "1972-09-16",
                "2025-11-20",
                "token alpha",
            ),
        ]
        (out / "sources.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )
        retriever = CorpusRetriever(corpus)
        current = retriever.search_corpus("token alpha")
        assert [row["metadata"]["document_id"] for row in current] == [
            "test-current-source"
        ]
        historical = retriever.search_corpus(
            "token alpha",
            as_of_date=date(2025, 11, 20),
            include_historical=True,
        )
        assert [row["metadata"]["document_id"] for row in historical] == [
            "test-historical-source"
        ]


def test_retrieval_normalizes_punctuation_and_preserves_chunk_checksum():
    with tempfile.TemporaryDirectory(
        prefix="retrieval-test-", dir=Path(__file__).resolve().parent
    ) as root:
        corpus = Path(root) / "corpus"
        out = corpus / "ingested"
        out.mkdir(parents=True)
        source = _row(
            "test-placeholder-source",
            "ACTIVE",
            "2025-11-21",
            None,
            "alpha beta punctuation 2025",
        )
        (out / "placeholder.jsonl").write_text(
            json.dumps(source) + "\n", encoding="utf-8"
        )
        rows = CorpusRetriever(corpus).search_corpus("alpha beta; 2025")
        assert rows and rows[0]["metadata"]["checksum"] == source["checksum"]


def test_empty_test_corpus_returns_no_passages(empty_test_corpus):
    assert CorpusRetriever(empty_test_corpus).search_corpus("section 53") == []


def test_gazette_fixture_metadata_and_text_checksum_are_valid(gazette_test_corpus):
    records = [
        json.loads(line)
        for path in Path(gazette_test_corpus).rglob("*.jsonl")
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 2
    for row in records:
        metadata = {key: value for key, value in row.items() if key != "exact_text"}
        validate_metadata(metadata)
        assert sha256(row["exact_text"].encode("utf-8")).hexdigest() == row["checksum"]
        assert row["document_id"] == "so-5319-e-2025"
        assert row["page_number"] == 2
        assert row["effective_from"] == "2025-11-21"
        assert row["publication_date"] == "2025-11-21"
        assert row["legal_status"] == "ACTIVE"
        assert row["source_version"] == "Gazette of India 2025-11-21"
        assert row["source_url"] == (
            "https://egazette.gov.in/WriteReadData/2025/267882.pdf"
        )
        assert len(row["sha256"]) == 64


def test_verified_gazette_fixture_is_retrievable(gazette_test_corpus):
    rows = CorpusRetriever(gazette_test_corpus).search_corpus(
        "sections 17 to 141 21st day of November 2025",
        document_ids=("so-5319-e-2025",),
    )
    assert len(rows) == 2
    assert any("sections 17 to 141" in row["text"] for row in rows)
    assert any("21st day of November, 2025" in row["text"] for row in rows)


def test_missing_gazette_source_routes_to_legal_counsel(empty_test_corpus):
    result = run_advisory(
        "When did Section 53 come into force?",
        {"domain": "OTHER"},
        research=ResearchAgent(CorpusRetriever(empty_test_corpus)),
    )
    assert result["decision"] == "LEGAL_COUNSEL_REVIEW"
    assert result["verification"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_official_gazette_supports_commencement_answer_for_section_53(
    gazette_test_corpus,
):
    result = run_advisory(
        "When did Section 53 come into force?",
        {"domain": "OTHER"},
        research=ResearchAgent(CorpusRetriever(gazette_test_corpus)),
    )
    assert result["decision"] == "ANSWER_WITH_CITATION"
    assert "2025-11-21" in result["advisory"]
    assert any(
        item.get("document_id") == "so-5319-e-2025"
        for item in result["verification"]["citations"]
    )
    citation = next(
        item
        for item in result["verification"]["citations"]
        if item.get("document_id") == "so-5319-e-2025"
    )
    assert citation["checksum"]
    assert citation["page_number"] == 2
