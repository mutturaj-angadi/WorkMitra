from datetime import date

REQUIRED = {
    "document_id",
    "statute_name",
    "section",
    "subsection",
    "clause",
    "provision_type",
    "legal_status",
    "effective_from",
    "effective_to",
    "source_url",
    "source_version",
    "page_number",
    "chunk_id",
}


def effective_on(metadata: dict, when: date, include_historical: bool = False) -> bool:
    """Return whether this corpus record is eligible for the requested legal date."""
    status = metadata.get("legal_status")
    permitted = {"ACTIVE"}
    if include_historical:
        permitted.update({"REPEALED", "HISTORICAL"})
    if status not in permitted:
        return False
    try:
        start = date.fromisoformat(str(metadata.get("effective_from", "")))
        end_value = metadata.get("effective_to")
        end = date.fromisoformat(str(end_value)) if end_value else None
    except (TypeError, ValueError):
        return False
    return start <= when and (end is None or when <= end)


def validate_metadata(metadata: dict) -> None:
    missing = REQUIRED - set(metadata)
    if missing:
        raise ValueError(f"Missing corpus metadata: {', '.join(sorted(missing))}")
    if metadata["legal_status"] not in {"ACTIVE", "REPEALED", "HISTORICAL", "UNKNOWN"}:
        raise ValueError(
            "legal_status must be ACTIVE, REPEALED, HISTORICAL, or UNKNOWN"
        )
    if metadata["legal_status"] == "ACTIVE" and not metadata["effective_from"]:
        raise ValueError("ACTIVE sources require an effective_from date")
