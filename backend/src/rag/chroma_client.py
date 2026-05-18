from __future__ import annotations

import logging
import os
import chromadb

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PATH = os.path.join(BASE_DIR, "data", "chroma")

COLLECTION_NAME = "video_content"

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def reset_collection() -> chromadb.Collection:
    """Delete and recreate the collection (needed when embedding dimensions change)."""
    global _collection
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection reset")
    return _collection


def upsert_chunks(chunks: list[dict]):
    """chunks: list of {id, embedding, document, metadata}"""
    col = get_collection()
    col.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        documents=[c["document"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )


def similarity_query(
    embedding: list[float], user_email: str, top_k: int = 5
) -> list[dict]:
    col = get_collection()
    try:
        total = col.count()
        if total == 0:
            return []

        # Clamp n_results to what's actually available
        n = min(top_k, total)

        results = col.query(
            query_embeddings=[embedding],
            n_results=n,
            where={"user_email": user_email},
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.error("ChromaDB query error: %s", e)
        return []

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    return [
        {
            "text": doc,
            "metadata": meta,
            "score": round(1.0 - dist, 4),
        }
        for doc, meta, dist in zip(docs, metas, distances)
    ]


def delete_user_vectors(user_email: str):
    """Remove all indexed chunks for a tenant before re-indexing."""
    col = get_collection()
    try:
        col.delete(where={"user_email": user_email})
    except Exception:
        pass
