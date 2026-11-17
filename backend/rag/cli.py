"""Fetch and idempotently ingest the authoritative corpus sources."""

import argparse
import json
import urllib.request
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse

from backend.rag.ingestion import ingest_pdf

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "corpus" / "source_manifest.json"
OFFICIAL_HOSTS = {
    "indiacode.nic.in",
    "labour.gov.in",
    "egazette.gov.in",
    "egazette.nic.in",
}


def verify_sources():
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = []
    for source in sources:
        metadata = source["metadata"]
        path = ROOT / source["path"]
        host = urlparse(source.get("download_url", "")).hostname
        item = {
            "document_id": metadata.get("document_id"),
            "source_url": source.get("download_url"),
            "official_host": bool(
                host
                and any(
                    host == allowed or host.endswith("." + allowed)
                    for allowed in OFFICIAL_HOSTS
                )
            ),
            "file_exists": path.is_file(),
            "status": "MISSING",
        }
        if path.is_file():
            payload = path.read_bytes()
            digest = sha256(payload).hexdigest()
            expected = metadata.get("sha256")
            item.update(
                pdf_signature=payload.startswith(b"%PDF-"),
                sha256=digest,
                checksum_matches=(digest == expected) if expected else None,
            )
            if not item["official_host"]:
                item["status"] = "NON_OFFICIAL_SOURCE"
            elif not item["pdf_signature"]:
                item["status"] = "INVALID_PDF"
            elif expected and digest != expected:
                item["status"] = "CHECKSUM_MISMATCH"
            else:
                item["status"] = "LOCAL_PDF_VERIFIED"
        elif not item["official_host"]:
            item["status"] = "NON_OFFICIAL_SOURCE"
        results.append(item)
    report = {"checked_at": datetime.now(UTC).isoformat(), "sources": results}
    print(json.dumps(report, indent=2))
    return report


def find_duplicates():
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_hash = {}
    missing = []
    for source in sources:
        path = ROOT / source["path"]
        if not path.is_file():
            missing.append(source["metadata"].get("document_id"))
            continue
        digest = sha256(path.read_bytes()).hexdigest()
        by_hash.setdefault(digest, []).append(source["metadata"].get("document_id"))
    duplicate_groups = [ids for ids in by_hash.values() if len(ids) > 1]
    return {"duplicate_groups": duplicate_groups, "missing_documents": missing}


def ingest_all(download=False, index=False, reembed=False):
    started = perf_counter()
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    report = []
    for source in rows:
        path = ROOT / source["path"]
        if not path.exists():
            if download:
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    request = urllib.request.Request(
                        source["download_url"],
                        headers={
                            "User-Agent": "WorkplaceComplianceDeskCorpusIngest/1.0"
                        },
                    )
                    with urllib.request.urlopen(request, timeout=25) as response:
                        path.write_bytes(response.read())
                except Exception as exc:  # noqa: BLE001 - record source failure and continue the manifest
                    report.append(
                        {
                            "document_id": source["metadata"]["document_id"],
                            "status": "DOWNLOAD_FAILED",
                            "error_type": type(exc).__name__,
                        }
                    )
                    continue
            else:
                report.append(
                    {
                        "document_id": source["metadata"]["document_id"],
                        "status": "SOURCE_FILE_MISSING",
                        "source_url": source["metadata"]["source_url"],
                    }
                )
                continue
        try:
            if path.read_bytes()[:5] != b"%PDF-":
                report.append(
                    {
                        "document_id": source["metadata"]["document_id"],
                        "status": "SOURCE_FILE_INVALID",
                        "detail": "Downloaded payload is not a PDF.",
                    }
                )
                continue
            result = ingest_pdf(path, source["metadata"], ROOT / "corpus" / "ingested")
            report.append(result)
        except Exception as exc:  # noqa: BLE001 - isolate extraction failure to this document
            report.append(
                {
                    "document_id": source["metadata"]["document_id"],
                    "status": "INGESTION_FAILED",
                    "error_type": type(exc).__name__,
                }
            )
    out = ROOT / "corpus" / "ingestion_report.json"
    total_chunks = sum(item.get("chunks", 0) for item in report)
    elapsed = max(perf_counter() - started, 0.000001)
    details = {
        "indexed_at": datetime.now(UTC).isoformat(),
        "documents_ready": sum(x.get("status") == "INDEX_READY" for x in report),
        "documents_missing": sum(
            x.get("status") == "SOURCE_FILE_MISSING" for x in report
        ),
        "documents_failed": sum(
            x.get("status")
            in {
                "DOWNLOAD_FAILED",
                "SOURCE_FILE_INVALID",
                "INGESTION_FAILED",
                "OCR_REQUIRED",
            }
            for x in report
        ),
        "chunks": total_chunks,
        "elapsed_seconds": round(elapsed, 6),
        "chunks_per_second": round(total_chunks / elapsed, 2),
        "source_versions": {
            x.get("document_id"): x.get("source_version")
            for x in report
            if x.get("status") == "INDEX_READY"
        },
    }
    out.write_text(
        json.dumps({"pipeline": details, "documents": report}, indent=2),
        encoding="utf-8",
    )
    vector_report = []
    if index:
        try:
            from backend.rag.vector_store import index_corpus

            vector_report = index_corpus(ROOT / "corpus" / "ingested", reembed=reembed)
        except Exception as exc:  # noqa: BLE001 - optional vector indexing must not abort lexical ingest
            vector_report = [
                {"status": "VECTOR_INDEX_FAILED", "error_type": type(exc).__name__}
            ]
    print(
        json.dumps(
            {
                "documents": len(report),
                "ready": details["documents_ready"],
                "missing": details["documents_missing"],
                "pipeline": details,
                "vector_index": vector_report,
                "report": str(out.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    return report


def main():
    parser = argparse.ArgumentParser(description="Idempotent official corpus ingest")
    parser.add_argument(
        "--download",
        action="store_true",
        help="download missing PDFs from official publisher URLs",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report missing source PDFs without downloading",
    )
    parser.add_argument(
        "--status", action="store_true", help="report local corpus status"
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="upsert extracted chunks into Chroma using local embeddings",
    )
    parser.add_argument(
        "--reembed",
        action="store_true",
        help="regenerate all embeddings using current EMBEDDING_MODEL",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="re-extract local PDFs and upsert vectors without deleting collections",
    )
    parser.add_argument(
        "--verify-sources",
        action="store_true",
        help="check official hosts, PDF signatures, and manifest hashes",
    )
    parser.add_argument(
        "--duplicates", action="store_true", help="compare local source PDF checksums"
    )
    parser.add_argument(
        "--validate-embeddings",
        action="store_true",
        help="connect to configured Chroma and inspect collection count/model",
    )
    parser.add_argument(
        "--retrieval-test", help="run lexical/semantic retrieval for a query"
    )
    args = parser.parse_args()
    if args.verify_sources:
        verify_sources()
    if args.duplicates:
        print(json.dumps(find_duplicates(), indent=2))
    if args.validate_embeddings:
        try:
            from backend.config import get_settings
            from backend.rag.vector_store import get_vector_store

            settings = get_settings()
            store = get_vector_store(settings.embedding_model, settings.chroma_url)
            print(
                json.dumps(
                    {
                        "status": "connected",
                        "collection_count": store.store._collection.count(),
                        "embedding_model": store.model_name,
                    },
                    indent=2,
                )
            )
        except Exception as exc:  # noqa: BLE001 - report type only, never connection details
            print(
                json.dumps({"status": "unavailable", "error_type": type(exc).__name__})
            )
    if args.retrieval_test:
        from backend.rag.retriever import CorpusRetriever

        matches = CorpusRetriever(ROOT / "corpus").search_corpus(args.retrieval_test)
        print(
            json.dumps(
                [
                    {
                        "chunk_id": p["metadata"].get("chunk_id"),
                        "document_id": p["metadata"].get("document_id"),
                        "section": p["metadata"].get("section"),
                        "page_number": p["metadata"].get("page_number"),
                        "source_url": p["metadata"].get("source_url"),
                        "score": p.get("score"),
                    }
                    for p in matches
                ],
                indent=2,
            )
        )
    if (
        args.check
        or args.status
        or args.download
        or args.index
        or args.rebuild
        or args.reembed
    ):
        ingest_all(
            download=args.download,
            index=args.index or args.rebuild,
            reembed=args.reembed,
        )


if __name__ == "__main__":
    main()
