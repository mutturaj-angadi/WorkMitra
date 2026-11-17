import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from pypdf import PdfReader

from backend.rag.chunking import split_sections
from backend.rag.metadata import validate_metadata


def extract_pdf(path: str | Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    return [
        (i + 1, (page.extract_text() or "").replace("\x00", "").strip())
        for i, page in enumerate(reader.pages)
    ]


def ingest_pdf(path: str | Path, metadata: dict, output_dir: str | Path) -> dict:
    """Extract/index-ready chunk JSON; OCR is reported as needed, never silently faked."""
    started = perf_counter()
    pages = extract_pdf(path)
    if not any(text for _, text in pages):
        return {
            "status": "OCR_REQUIRED",
            "chunks": 0,
            "document_id": metadata.get("document_id"),
            "pages": len(pages),
            "indexed_at": datetime.now(UTC).isoformat(),
        }
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    source = Path(path).read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    records = []
    for page, text in pages:
        for idx, chunk in enumerate(split_sections(text, page)):
            row = {
                **metadata,
                "document_category": metadata.get(
                    "document_category", metadata.get("provision_type", "UNKNOWN")
                ),
                "document_version": metadata.get("source_version"),
                "section": chunk.section
                if chunk.section != "UNKNOWN"
                else metadata.get("section", "UNKNOWN"),
                "page_number": page,
                "chunk_id": f"{metadata['document_id']}-{page}-{idx}",
                "exact_text": chunk.text,
                "checksum": hashlib.sha256(chunk.text.encode()).hexdigest(),
            }
            validate_metadata(
                {
                    k: row[k]
                    for k in [
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
                    ]
                }
            )
            records.append(row)
    out = target / f"{metadata['document_id']}.jsonl"
    existing = out.read_text(encoding="utf-8") if out.exists() else ""
    serialized = (
        "\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n"
    )
    if existing != serialized:
        out.write_text(serialized, encoding="utf-8")
    elapsed = max(perf_counter() - started, 0.000001)
    return {
        "status": "INDEX_READY",
        "document_id": metadata["document_id"],
        "chunks": len(records),
        "pages": len(pages),
        "sha256": digest,
        "output": str(out),
        "source_version": metadata.get("source_version"),
        "indexed_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(elapsed, 6),
        "chunks_per_second": round(len(records) / elapsed, 2),
    }
