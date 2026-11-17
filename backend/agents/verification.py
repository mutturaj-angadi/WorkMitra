"""Independent provenance and applicability checks for retrieved evidence."""

import re
from collections import defaultdict
from datetime import date
from hashlib import sha256
from urllib.parse import urlparse

from backend.schemas import VerificationOutput

OFFICIAL_HOSTS = {
    "indiacode.nic.in",
    "labour.gov.in",
    "egazette.nic.in",
    "egazette.gov.in",
}


class VerificationAgent:
    name = "verification-agent"

    def verify(
        self,
        evidence: list[dict],
        relevant_date: date | None = None,
        question: str = "",
        domain: str = "",
        case_facts: dict | None = None,
    ) -> dict:
        if not evidence:
            return VerificationOutput(
                status="INSUFFICIENT_EVIDENCE",
                verified=False,
                reasons=["No source passages were retrieved."],
            ).model_dump()
        when = relevant_date or date.today()
        valid, issues, excluded, seen = [], [], [], set()
        case_facts = case_facts or {}
        versions_by_document = defaultdict(set)
        for passage in evidence:
            metadata = passage.get("metadata", {})
            document_id = metadata.get("document_id")
            version = metadata.get("source_version")
            if document_id and version:
                versions_by_document[document_id].add(str(version))
        conflicting_documents = {
            document_id
            for document_id, versions in versions_by_document.items()
            if len(versions) > 1
        }
        is_gratuity = domain.upper() == "GRATUITY" or any(
            word in question.casefold()
            for word in ("gratuity", "fixed-term", "fixed term")
        )
        for item in evidence:
            metadata = item.get("metadata", {})
            text = item.get("text", "")
            chunk_id = metadata.get("chunk_id")
            if metadata.get("document_id") in conflicting_documents:
                issues.append(
                    f"Conflicting source versions were retrieved for {metadata.get('document_id')}."
                )
                continue
            if not isinstance(text, str) or not text.strip():
                issues.append("Passage has no exact source text.")
                continue
            checksum = metadata.get("checksum")
            if checksum and sha256(text.encode("utf-8")).hexdigest() != checksum:
                issues.append("Passage text does not match its indexed checksum.")
                continue
            if not chunk_id or chunk_id in seen:
                issues.append("Passage has no unique stable chunk identifier.")
                continue
            seen.add(chunk_id)
            if metadata.get("legal_status") != "ACTIVE":
                excluded.append(
                    {
                        "chunk_id": chunk_id,
                        "reason": f"Legal status is {metadata.get('legal_status', 'UNKNOWN')}.",
                    }
                )
                continue
            commencement_question = any(
                term in question.casefold()
                for term in (
                    "commenced",
                    "commencement",
                    "came into force",
                    "come into force",
                    "effective date",
                )
            )
            is_section53_notice = (
                commencement_question
                and metadata.get("document_id") == "so-5319-e-2025"
                and metadata.get("provision_type") == "COMMENCEMENT_NOTIFICATION"
            )
            if metadata.get("provision_type") not in {"ACT", "STATUTE", "SECTION"}:
                if not is_section53_notice:
                    excluded.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": "Non-statutory guidance cannot independently support a statutory determination.",
                        }
                    )
                    continue
                notice_text = " ".join(text.casefold().split())
                if not (
                    "21st day of november, 2025" in notice_text
                    or "sections 17 to 141" in notice_text
                ):
                    excluded.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": "This Gazette chunk does not contain the date or provision range needed for the commencement claim.",
                        }
                    )
                    continue
            host = urlparse(metadata.get("source_url", "")).hostname
            if not host or not any(
                host == d or host.endswith("." + d) for d in OFFICIAL_HOSTS
            ):
                issues.append("Source host is not an approved official publisher.")
                continue
            version = metadata.get("source_version")
            if not version or str(version).casefold() == "unverified":
                issues.append("Source version is not verified.")
                continue
            try:
                start = date.fromisoformat(metadata["effective_from"])
                end = (
                    date.fromisoformat(metadata["effective_to"])
                    if metadata.get("effective_to")
                    else None
                )
            except (KeyError, TypeError, ValueError):
                issues.append("Provision effective dates are missing or invalid.")
                continue
            if start > when or (end and end < when):
                excluded.append(
                    {
                        "chunk_id": chunk_id,
                        "reason": f"Provision is not in force on {when.isoformat()}.",
                    }
                )
                continue
            # A gratuity case requires the target primary provision, never an
            # unrelated active statute returned by lexical overlap.
            if is_gratuity:
                document_id = str(metadata.get("document_id", "")).casefold()
                section = str(metadata.get("section", ""))
                if "code-social-security-2020" not in document_id or not re.match(
                    r"\s*53(?:\D|$)", section
                ):
                    excluded.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": "Gratuity determination requires section 53 of the Code on Social Security, 2020.",
                        }
                    )
                    continue
                normalized = " ".join(text.casefold().split())
                if "expiration of fixed term employment" not in normalized:
                    issues.append(
                        "Section 53 evidence does not include the fixed-term expiration proviso text."
                    )
                    continue
            # Citations are the actual retrieved records, so a client can resolve
            # every citation to one of the exact passages in the run trace.
            valid.append(metadata)

        if is_gratuity:
            facts_ok, missing_facts = self._fixed_term_facts(question, case_facts)
            notices = [
                p
                for p in evidence
                if p.get("metadata", {}).get("document_id") == "so-5319-e-2025"
            ]
            notice_text = " ".join(
                " ".join(str(p.get("text", "")).casefold().split()) for p in notices
            )
            commencement_found = (
                "21st day of november, 2025" in notice_text
                and "17 to 141" in notice_text
                and any(
                    urlparse(p.get("metadata", {}).get("source_url", "")).hostname
                    == "egazette.gov.in"
                    for p in notices
                )
            )
            if not commencement_found:
                issues.append(
                    "The official section 53 commencement notification is not among the retrieved evidence."
                )
            if not valid:
                issues.append(
                    "No verified section 53 primary-source passage supports this gratuity case."
                )
            if not facts_ok and valid and commencement_found:
                return VerificationOutput(
                    status="REQUIRES_MORE_INFORMATION",
                    verified=False,
                    reasons=[
                        f"Required case fact is not established: {item}."
                        for item in missing_facts
                    ],
                    citations=[*valid, *(p["metadata"] for p in notices)],
                    excluded=excluded,
                ).model_dump()
            if issues:
                return VerificationOutput(
                    status="INSUFFICIENT_EVIDENCE",
                    verified=False,
                    reasons=issues,
                    excluded=excluded,
                ).model_dump()
            valid.extend(p["metadata"] for p in notices)
        if issues or not valid:
            reasons = issues or [
                f"No current primary statutory provision was retrieved for {when.isoformat()}."
            ]
            status = "INSUFFICIENT_EVIDENCE"
            return VerificationOutput(
                status=status, verified=False, reasons=reasons, excluded=excluded
            ).model_dump()
        return VerificationOutput(
            status="VERIFIED", verified=True, citations=valid, excluded=excluded
        ).model_dump()

    @staticmethod
    def _fixed_term_facts(question: str, facts: dict) -> tuple[bool, list[str]]:
        text = question.casefold()
        contract_type = str(facts.get("contract_type", "")).casefold()
        fixed_term = "fixed" in contract_type or bool(re.search(r"fixed[ -]term", text))
        directly_employed = "direct" in contract_type or bool(
            re.search(
                r"\b(?:directly employed|employed directly|direct employee)\b", text
            )
        )
        written = facts.get("contract_written") is True or (
            "written" in text and "contract" in text
        )
        duration = facts.get("contract_duration_months")
        if duration is None:
            match = re.search(r"\b(\d{1,3})\s*[- ]?months?\b", text)
            if match:
                duration = int(match.group(1))
            else:
                years = re.search(r"\b(\d{1,2})\s*years?\b", text)
                duration = int(years.group(1)) * 12 if years else None
        completed = facts.get("employment_end") is not None or bool(
            re.search(r"\b(completed|expired|expiry|expiration|ended)\b", text)
        )
        start_after = False
        start = facts.get("employment_start")
        if isinstance(start, date):
            start_after = start >= date(2025, 11, 21)
        elif isinstance(start, str):
            try:
                start_after = date.fromisoformat(start) >= date(2025, 11, 21)
            except ValueError:
                pass
        start_after = start_after or bool(
            re.search(r"after\s+21\s+(?:nov(?:ember)?\s+2025|11[/-]21[/-]2025)", text)
        )
        missing = []
        if not fixed_term:
            missing.append("fixed-term status")
        if not directly_employed:
            missing.append("direct employment by the hiring employer")
        if not written:
            missing.append("written contract")
        if not isinstance(duration, int) or duration < 12:
            missing.append("contract duration of at least 12 months")
        if not completed:
            missing.append("contract completion or expiry")
        if not start_after:
            missing.append("employment commencing on or after 2025-11-21")
        return not missing, missing
