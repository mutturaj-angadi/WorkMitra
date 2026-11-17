"""Fixed-term safety regressions use real source text and never synthesize law."""

from copy import deepcopy
from datetime import date

from backend.agents.research import ResearchAgent
from backend.agents.verification import VerificationAgent
from backend.orchestrator.graph import run_advisory
from backend.rag.retriever import CorpusRetriever

NOTICE = "so-5319-e-2025"
FAQ = "mole-labour-codes-faq-2026-03"


def _notice_passages():
    return CorpusRetriever("corpus").search_corpus(
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


def test_01_complete_18_month_case_facts_are_recognized_without_proving_entitlement():
    complete, missing = VerificationAgent._fixed_term_facts(
        "Does gratuity apply?", _complete_case_facts()
    )
    assert complete and not missing
    # The actual workflow still requires Section 53 primary text; it is absent.
    result = run_advisory(
        "Does gratuity apply after my completed 18 month written fixed-term contract?",
        _complete_case_facts(),
        research=ResearchAgent(CorpusRetriever("corpus")),
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


def test_03_ministry_faq_without_commencement_and_primary_code_does_not_verify():
    faq = CorpusRetriever("corpus").search_corpus(
        "fixed term gratuity", limit=8, document_ids=(FAQ,)
    )
    result = VerificationAgent().verify(
        faq,
        question="Is gratuity payable after a fixed-term contract?",
        domain="GRATUITY",
        case_facts=_complete_case_facts(),
    )
    assert not result["verified"]
    assert not result["citations"]


def test_04_commencement_notice_is_not_effective_before_its_date():
    result = VerificationAgent().verify(
        _notice_passages(),
        relevant_date=date(2025, 11, 20),
        question="When did Section 53 come into force?",
    )
    assert not result["verified"]


def test_05_wrong_statutory_section_cannot_support_gratuity():
    passages = deepcopy(_notice_passages())
    passages[0]["metadata"]["section"] = "54"
    result = VerificationAgent().verify(
        passages,
        question="Is gratuity payable after a fixed-term contract?",
        domain="GRATUITY",
        case_facts=_complete_case_facts(),
    )
    assert not result["verified"]


def test_06_repealed_source_is_excluded():
    passages = deepcopy(_notice_passages())
    for passage in passages:
        passage["metadata"]["legal_status"] = "REPEALED"
    result = VerificationAgent().verify(
        passages, question="When did Section 53 come into force?"
    )
    assert not result["verified"]


def test_07_conflicting_versions_of_same_source_are_rejected():
    passages = _notice_passages()[:2]
    assert len(passages) == 2
    passages[1]["metadata"]["source_version"] = "conflicting version marker"
    result = VerificationAgent().verify(
        passages, question="When did Section 53 come into force?"
    )
    assert not result["verified"]
    assert any("Conflicting source versions" in reason for reason in result["reasons"])


def test_08_bad_passage_checksum_cannot_be_cited():
    passages = deepcopy(_notice_passages())
    for passage in passages:
        passage["metadata"]["checksum"] = "0" * 64
    result = VerificationAgent().verify(
        passages, question="When did Section 53 come into force?"
    )
    assert not result["verified"]
    assert not result["citations"]


def test_09_insufficient_evidence_escalates():
    result = run_advisory(
        "Is gratuity payable after a fixed-term contract?",
        _complete_case_facts(),
        research=ResearchAgent(CorpusRetriever("backend/tests/fixtures/empty")),
    )
    assert result["decision"] == "LEGAL_COUNSEL_REVIEW"


def test_10_official_gazette_supports_a_cited_commencement_answer():
    result = run_advisory(
        "When did Section 53 come into force?",
        {"domain": "OTHER"},
        research=ResearchAgent(CorpusRetriever("corpus")),
    )
    assert result["decision"] == "ANSWER_WITH_CITATION"
    assert "2025-11-21" in result["advisory"]
    assert any(
        item.get("document_id") == NOTICE
        for item in result["verification"]["citations"]
    )
