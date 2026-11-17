# Retrieval and corpus ingestion

The manifest-driven CLI validates PDF signatures and checksums, extracts page text with `pypdf`, removes NUL bytes, detects image-only documents (`OCR_REQUIRED`), and chunks by section. Default chunks are 2,200 characters with a 200-character overlap. Records retain exact text, document identity/category/version, source URL, page, section, legal status, effective interval, source version, checksum, and stable chunk ID. Re-ingestion is deterministic and avoids rewriting unchanged JSONL.

Lexical retrieval is available locally and ranks exact-source chunks by query-term overlap, with legal status/effective-date filters. Optional source/date scopes support targeted workflows. Semantic retrieval requires a configured embedding model and available Chroma service; it is not configured or verified in the current local runtime. Do not describe fallback as proof that semantic retrieval works.

## Latest verified corpus state

The manifest contains six sources. Three local PDFs passed signature/checksum checks and produced 58 chunks: Gazette S.O. 5319(E), its corrigendum S.O. 5936(E), and Ministry of Labour FAQs. Three primary-law PDFs are missing: Code on Social Security, POSH Act, and historical Payment of Gratuity Act. The current source register explains official locations and download limitations.

The missing Code section 53 evidence means statutory fixed-term gratuity eligibility is not established by the local corpus. That scenario must escalate to legal counsel. Do not hardcode the legal conclusion or use search snippets as a substitute for verified primary text. The POSH workflow likewise routes to human review.

Rebuild/check locally:

```powershell
python -m backend.rag.cli --check
python -m backend.rag.cli --verify-sources --duplicates
```

Generated `corpus/ingested/*.jsonl` and `corpus/ingestion_report.json` are ignored by Git; regenerate them from the manifest and available bundled PDFs. Optional embeddings validation:

```powershell
python -m backend.rag.cli --validate-embeddings
```

Retrieval caching applies to passages, never final legal answers. Corpus filenames, modification times, and sizes affect the cache key. An embedding model/vector service and retrieval relevance are not validated. Latest evaluation retrieval precision/recall are 0.0, so retrieval quality needs improvement before broader use.
