import json
import logging
import re
from datetime import date
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from prometheus_client import Counter, Histogram

from backend.config import get_settings
from backend.rag.chunking import split_sections
from backend.rag.metadata import effective_on, validate_metadata
from backend.reliability import TTLCache

RETRIEVAL_CACHE = Counter(
    "compliance_retrieval_cache_total", "Retrieval cache hits and misses", ["result"]
)
RETRIEVAL_LATENCY = Histogram(
    "compliance_retrieval_seconds", "Corpus retrieval duration", ["cache"]
)
logger = logging.getLogger("compliance_desk.retrieval")
WORD = re.compile(r"[\w]+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in WORD.findall(text) if len(token) > 2}


class CorpusRetriever:
    """Exact-text lexical fallback. Empty corpus is deliberately an evidence gap."""

    def __init__(self, root: str | Path = "corpus"):
        self.root = Path(root)
        self.cache = TTLCache(max_items=512, ttl_seconds=45)

    def search_corpus(
        self,
        query: str,
        limit: int = 5,
        as_of_date: date | None = None,
        include_historical: bool = False,
        document_ids: tuple[str, ...] | None = None,
    ) -> list[dict]:
        started = perf_counter()
        relevant_date = as_of_date or date.today()
        try:
            versions = sorted(
                (
                    p.relative_to(self.root).as_posix(),
                    p.stat().st_mtime_ns,
                    p.stat().st_size,
                )
                for p in self.root.rglob("*.jsonl")
            )
        except OSError:
            versions = []
        corpus_version = sha256(repr(versions).encode()).hexdigest()
        cache_key = (
            str(self.root.resolve()),
            corpus_version,
            query.casefold(),
            limit,
            relevant_date.isoformat(),
            include_historical,
            tuple(sorted(document_ids or ())),
        )
        cached = self.cache.get(cache_key)
        if cached is not None:
            RETRIEVAL_CACHE.labels("hit").inc()
            RETRIEVAL_LATENCY.labels("hit").observe(perf_counter() - started)
            return cached
        RETRIEVAL_CACHE.labels("miss").inc()
        tokens = _tokens(query)
        ranked = []
        # Ingestion emits exact-text JSONL records with provision-level provenance.
        for path in self.root.rglob("*.jsonl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = row.get("exact_text", "")
                metadata = {k: v for k, v in row.items() if k != "exact_text"}
                if not text.strip():
                    continue
                try:
                    validate_metadata(metadata)
                except (ValueError, KeyError):
                    continue
                if document_ids and metadata.get("document_id") not in document_ids:
                    continue
                if not effective_on(metadata, relevant_date, include_historical):
                    continue
                score = len(tokens & _tokens(text))
                if score:
                    ranked.append({"text": text, "metadata": metadata, "score": score})
        for path in self.root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            for chunk in split_sections(text):
                words = _tokens(chunk.text)
                score = len(tokens & words)
                if score:
                    metadata = {
                        "document_id": path.stem,
                        "statute_name": path.stem,
                        "section": chunk.section,
                        "subsection": "",
                        "clause": "",
                        "provision_type": "UNKNOWN",
                        "legal_status": "UNKNOWN",
                        "effective_from": None,
                        "effective_to": None,
                        "source_url": "",
                        "source_version": "unverified",
                        "page_number": chunk.page_number,
                        "chunk_id": f"{path.stem}-{chunk.parent_id}-{chunk.child_index}",
                    }
                    validate_metadata(metadata)
                    ranked.append(
                        {"text": chunk.text, "metadata": metadata, "score": score}
                    )
        # Optional hybrid retrieval: semantic results are unioned with exact lexical matches.
        settings = get_settings()
        if settings.embedding_model:
            try:
                from backend.rag.vector_store import get_vector_store

                semantic = get_vector_store(
                    settings.embedding_model, settings.chroma_url
                ).search(query, limit)
                combined = {p["metadata"]["chunk_id"]: p for p in ranked}
                for rank, item in enumerate(semantic, 1):
                    key = item["metadata"].get("chunk_id", "")
                    if not effective_on(
                        item.get("metadata", {}), relevant_date, include_historical
                    ):
                        continue
                    if (
                        document_ids
                        and item.get("metadata", {}).get("document_id")
                        not in document_ids
                    ):
                        continue
                    if key:
                        old = combined.get(key)
                        item["score"] = item["score"] + (old["score"] if old else 0)
                        item["retrieval"] = "hybrid" if old else "semantic"
                        combined[key] = item
                ranked = list(combined.values())
            # A disconnected vector backend must degrade to exact lexical search.
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Semantic retrieval unavailable; using lexical corpus fallback",
                    extra={"error_type": type(exc).__name__},
                )
        result = sorted(ranked, key=lambda x: x["score"], reverse=True)[:limit]
        self.cache.set(cache_key, result)
        RETRIEVAL_LATENCY.labels("miss").observe(perf_counter() - started)
        return result

    def search_keyword(
        self,
        query: str,
        limit: int = 5,
        as_of_date: date | None = None,
        include_historical: bool = False,
    ):
        return self.search_corpus(query, limit, as_of_date, include_historical)

    def lookup_section(
        self,
        section: str,
        as_of_date: date | None = None,
        include_historical: bool = False,
    ):
        return [
            p
            for p in self.search_corpus(section, 20, as_of_date, include_historical)
            if section.casefold() in p["metadata"]["section"].casefold()
        ]

    def get_request_fields(self, request: dict):
        return {k: v for k, v in request.items() if v is not None}

    def search_related_provisions(
        self,
        passage: dict,
        query: str,
        as_of_date: date | None = None,
        include_historical: bool = False,
    ):
        return self.search_corpus(
            query + " proviso exception explanation",
            5,
            as_of_date,
            include_historical,
        )

    def check_legal_status(self, passage: dict):
        return passage.get("metadata", {}).get("legal_status", "UNKNOWN")
