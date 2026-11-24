"""Gemini wrapper: text/JSON generation and batched embeddings with retries."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

EMBED_BATCH = 100


class AIUnavailable(RuntimeError):
    """Gemini is not configured or failed after retries."""


class AIRateLimited(AIUnavailable):
    """Gemini quota exhausted (the free tier allows only a few requests per minute)."""


def _is_rate_limit(exc: BaseException) -> bool:
    return isinstance(exc, genai_errors.APIError) and exc.code == 429


def _is_retryable(exc: BaseException) -> bool:
    return _is_rate_limit(exc) or (isinstance(exc, genai_errors.APIError) and (exc.code or 0) >= 500)


def _wrap(exc: Exception, message: str) -> AIUnavailable:
    if _is_rate_limit(exc):
        return AIRateLimited(
            "Gemini quota reached. Wait a minute and try again (or enable billing on the API key)."
        )
    return AIUnavailable(message)


class Gemini:
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key:
            raise AIUnavailable("GEMINI_API_KEY is not configured")
        # v1beta: system instructions and JSON schemas are not available on the v1 surface.
        self._client = genai.Client(
            api_key=settings.gemini_api_key, http_options=types.HttpOptions(api_version="v1beta")
        )
        self._model = settings.gemini_model
        self._embed_model = settings.embed_model
        self.embed_dims = settings.embed_dims

    @property
    def embed_signature(self) -> str:
        return f"{self._embed_model}@{self.embed_dims}"

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential_jitter(initial=8, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _generate(self, contents: str, config: types.GenerateContentConfig) -> str:
        res = self._client.models.generate_content(model=self._model, contents=contents, config=config)
        return res.text or ""

    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.7) -> str:
        try:
            return self._generate(
                prompt, types.GenerateContentConfig(system_instruction=system, temperature=temperature)
            )
        except Exception as exc:
            logger.warning("Gemini generate failed: %s", str(exc)[:200])
            raise _wrap(exc, "The AI service failed to respond") from exc

    def generate_json(self, prompt: str, schema: type[T], *, system: str | None = None) -> T:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.6,
            response_mime_type="application/json",
            response_schema=schema,
        )
        try:
            raw = self._generate(prompt, config)
        except Exception as exc:
            logger.warning("Gemini JSON generation failed: %s", str(exc)[:200])
            raise _wrap(exc, "The AI service failed to respond") from exc
        try:
            return schema.model_validate_json(raw)
        except ValueError as exc:
            logger.warning("Gemini returned JSON that does not match %s", schema.__name__)
            raise AIUnavailable("The AI service returned an invalid response") from exc

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential_jitter(initial=8, max=60),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        res = self._client.models.embed_content(
            model=self._embed_model,
            contents=texts,
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=self.embed_dims),
        )
        vectors = [list(e.values or []) for e in (res.embeddings or [])]
        if len(vectors) != len(texts) or any(len(v) != self.embed_dims for v in vectors):
            raise RuntimeError("Embedding response shape mismatch")
        return vectors

    def embed(self, texts: list[str], *, task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        """Embeds in batches. Raises instead of ever returning placeholder vectors."""
        out: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH):
            try:
                out.extend(self._embed(texts[i : i + EMBED_BATCH], task))
            except Exception as exc:
                logger.warning("Embedding batch failed: %s", str(exc)[:200])
                raise _wrap(exc, "Embedding service failed") from exc
        return out


@lru_cache
def _cached(api_key: str) -> Gemini:
    return Gemini(get_settings())


def get_gemini() -> Gemini:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise AIUnavailable("GEMINI_API_KEY is not configured")
    return _cached(settings.gemini_api_key)
