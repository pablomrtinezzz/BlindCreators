from __future__ import annotations

import logging
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIMS = 3072

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


def embed_text(text: str) -> list[float]:
    client = _get_client()
    result = client.models.embed_content(model=EMBED_MODEL, contents=text)
    return result.embeddings[0].values


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Sequential embedding — Gemini doesn't support true batch embed."""
    embeddings: list[list[float]] = []
    for text in texts:
        try:
            embeddings.append(embed_text(text))
        except Exception as e:
            logger.error("Embedding failed: %s", e)
            embeddings.append([0.0] * EMBED_DIMS)
    return embeddings
