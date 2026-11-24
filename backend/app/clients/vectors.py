"""ChromaDB access. One collection per user: tenant isolation without relying on filters."""

from __future__ import annotations

import logging
import threading

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.config import get_settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_client: ClientAPI | None = None


def _get_client() -> ClientAPI:
    global _client
    with _lock:
        if _client is None:
            path = get_settings().chroma_path
            path.mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(path=str(path))
        return _client


def collection_name(user_id: int) -> str:
    return f"user_{user_id}"


def user_collection(user_id: int, embed_signature: str) -> Collection:
    """Returns the user's collection, recreating it if the embedding model/dims changed."""
    client = _get_client()
    name = collection_name(user_id)
    col = client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine", "embed": embed_signature}
    )
    if (col.metadata or {}).get("embed") != embed_signature:
        logger.info("Embedding model changed for %s: rebuilding collection", name)
        client.delete_collection(name)
        col = client.create_collection(name=name, metadata={"hnsw:space": "cosine", "embed": embed_signature})
    return col


def existing_collection(user_id: int) -> Collection | None:
    try:
        return _get_client().get_collection(collection_name(user_id))
    except Exception:
        return None


def delete_user_collection(user_id: int) -> None:
    try:
        _get_client().delete_collection(collection_name(user_id))
    except Exception:
        logger.debug("No collection to delete for user %s", user_id)
