"""Optional LangChain/Chroma semantic index using local Sentence Transformers."""

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from backend.config import get_settings


class LocalSentenceEmbeddings:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(
            [text], normalize_embeddings=True, show_progress_bar=False
        )[0]
        return vector.tolist()


class ChromaVectorStore:
    def __init__(
        self,
        model_name: str | None = None,
        url: str | None = None,
        persist_directory: str = "chroma_data",
    ):
        import chromadb
        from langchain_chroma import Chroma

        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        if not self.model_name:
            raise ValueError("Set EMBEDDING_MODEL at runtime to enable vector indexing")
        self.embeddings = LocalSentenceEmbeddings(self.model_name)
        address = url or settings.chroma_url
        if address:
            parsed = urlparse(address)
            self.client = chromadb.HttpClient(
                host=parsed.hostname or "localhost",
                port=parsed.port or (443 if parsed.scheme == "https" else 8000),
                ssl=parsed.scheme == "https",
            )
            self.store = Chroma(
                client=self.client,
                collection_name="workplace_legal_corpus",
                embedding_function=self.embeddings,
            )
        else:
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            self.store = Chroma(
                collection_name="workplace_legal_corpus",
                embedding_function=self.embeddings,
                persist_directory=persist_directory,
            )

    @staticmethod
    def _safe_metadata(item: dict, model_name: str) -> dict:
        return {
            **{
                k: (
                    v
                    if isinstance(v, (str, int, float, bool))
                    else ""
                    if v is None
                    else json.dumps(v, ensure_ascii=False)
                )
                for k, v in item.items()
                if k not in {"exact_text"}
            },
            "embedding_model": model_name,
        }

    def index_jsonl(self, source: str | Path, reembed: bool = False) -> dict:
        docs = []
        ids = []
        metadata = []
        skipped = 0
        for line in Path(source).read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            chunk_id = item["chunk_id"]
            text = item["exact_text"]
            safe = self._safe_metadata(item, self.model_name)
            if not reembed:
                existing = self.store.get(ids=[chunk_id], include=["metadatas"])
                if existing.get("ids") and existing.get("metadatas"):
                    current = existing["metadatas"][0]
                    if (
                        current.get("checksum") == item.get("checksum")
                        and current.get("embedding_model") == self.model_name
                    ):
                        skipped += 1
                        continue
            docs.append(text)
            ids.append(chunk_id)
            metadata.append(safe)
        if ids:
            vectors = self.embeddings.embed_documents(docs)
            self.store._collection.upsert(
                ids=ids, documents=docs, metadatas=metadata, embeddings=vectors
            )
        return {
            "source": str(source),
            "indexed": len(ids),
            "skipped": skipped,
            "embedding_model": self.model_name,
            "reembedded": reembed,
        }

    def search(self, query: str, limit: int = 5) -> list[dict]:
        found = self.store.similarity_search_with_relevance_scores(query, k=limit)
        return [
            {
                "text": doc.page_content,
                "metadata": {
                    k: v for k, v in doc.metadata.items() if k != "embedding_model"
                },
                "score": float(score),
                "retrieval": "semantic",
            }
            for doc, score in found
        ]


@lru_cache(maxsize=2)
def get_vector_store(model_name: str, url: str) -> ChromaVectorStore:
    return ChromaVectorStore(model_name=model_name, url=url)


def index_corpus(
    directory: str | Path = "corpus/ingested", reembed: bool = False
) -> list[dict]:
    settings = get_settings()
    store = get_vector_store(settings.embedding_model, settings.chroma_url)
    return [
        store.index_jsonl(path, reembed=reembed)
        for path in Path(directory).glob("*.jsonl")
    ]
