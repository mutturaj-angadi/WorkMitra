"""Fixed-term safety regressions use isolated, verified test evidence."""

from copy import deepcopy
from datetime import date
from pathlib import Path

from backend.agents.research import ResearchAgent
from backend.agents.verification import VerificationAgent
from backend.orchestrator.graph import run_advisory
from backend.rag.retriever import CorpusRetriever

NOTICE = "so-5319-e-2025"


def _notice_passages(corpus: Path):
    return CorpusRetriever(corpus).search_corpus(
        "section 53 sections 17 to 141 21st November 2025 commencement",
        limit=8,
        document_ids=(NOTICE,),
    )


def _complete_case_facts():
    return {
        "contract_type": "direct fixed-term",
        "contract_written": True,
        "contract_duration_months": 18,
        "employment_start": "2025-11-22",
        "employment_end": "2027-05-21",
    }


def test_01_complete_18_month_case_facts_do_not_prove_entitlement(
    empty_test_corpus,
):
    complete, missing = VerificationAgent._fixed_term_facts(
        "Does gratuity apply?", _complete_case_facts()
    )
    assert complete and not missing
    result = run_advisory(
        "Does gratuity apply after my completed 18 month written fixed-term contract?",
        _complete_case_facts(),
        research=ResearchAgent(CorpusRetriever(empty_test_corpus)),
    )
    assert result["decision"] == "LEGAL_COUNSEL_REVIEW"


def test_02_missing_contract_details_are_reported():
    complete, missing = VerificationAgent._fixed_term_facts(
        "Does gratuity apply?", {"contract_type": "fixed-term"}
    )
    assert not complete
    assert {
        "written contract",
        "contract duration of at least 12 months",
        "contract completion or expiry",
    }.issubset(set(missing))


def test_03_gazette_commencement_notice_alone_does_not_verify_gratuity(
    gazette_test_corpus,
):
    passages = _notice_passages(gazette_test_corpus)
    result = VerificationAgent().verify(
        passages,
        question="Is gratuity payable after a fixed-term contract?",
        domain="GRATUITY",
        case_facts=_complete_case_facts(),
    )
    assert not result["verified"]
    assert not result["citations"]


def test_04_commencement_notice_is_not_effective_before_its_date(
    gazette_test_corpus,
):
    result = VerificationAgent().verify(
        _notice_passages(gazette_test_corpus),
        relevant_date=date(2025, 11, 20),
        question="When did Section 53 come into force?",
    )
    assert not result["verified"]


def test_05_wrong_statutory_section_cannot_support_gratuity(
    gazette_test_corpus,
):
    passages = _notice_passages(gazette_test_corpus)
    # Adversarial metadata mutation only: it deliberately mislabels a Gazette
    # passage as Code section 54 to exercise the verifier's section-53 guard.
    wrong_section = deepcopy(passages[0])
    wrong_section["metadata"].update(
        {
            "document_id": "code-social-security-2020",
            "statute_name": "Code on Social Security, 2020 (test mutation)",
            "provision_type": "ACT",
            "section": "54",
        }
    )
    result = VerificationAgent().verify(
        [wrong_section, *passages],
        question="Is gratuity payable after a fixed-term contract?",
        domain="GRATUITY",
        case_facts=_complete_case_facts(),
    )
    assert not result["verified"]
    assert any("requires section 53" in item["reason"] for item in result["excluded"])


def test_06_repealed_source_is_excluded(gazette_test_corpus):
    passages = deepcopy(_notice_passages(gazette_test_corpus))
    for passage in passages:
        passage["metadata"]["legal_status"] = "REPEALED"
    result = VerificationAgent().verify(
        passages, question="When did Section 53 come into force?"
    )
    assert not result["verified"]


def test_07_conflicting_versions_of_same_source_are_rejected(
    gazette_test_corpus,
):
    passages = _notice_passages(gazette_test_corpus)
    assert len(passages) == 2
    passages[1]["metadata"]["source_version"] = "conflicting version marker"
    result = VerificationAgent().verify(
        passages, question="When did Section 53 come into force?"
    )
    assert not result["verified"]
    assert any("Conflicting source versions" in reason for reason in result["reasons"])


def test_08_bad_passage_checksum_cannot_be_cited(gazette_test_corpus):
    passages = deepcopy(_notice_passages(gazette_test_corpus))
    for passage in passages:
        passage["metadata"]["checksum"] = "0" * 64
    result = VerificationAgent().verify(
        passages, question="When did Section 53 come into force?"
    )
    assert not result["verified"]
    assert not result["citations"]


def test_09_missing_gazette_evidence_escalates_without_index_error(
    empty_test_corpus,
):
    result = run_advisory(
        "When did Section 53 come into force?",
        {"domain": "OTHER"},
        research=ResearchAgent(CorpusRetriever(empty_test_corpus)),
    )
    assert result["decision"] == "LEGAL_COUNSEL_REVIEW"
    assert result["verification"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_10_valid_gazette_fixture_supports_cited_commencement_answer(
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
        item.get("document_id") == NOTICE
        for item in result["verification"]["citations"]
    )
