"""Application settings, loaded once from environment variables / .env files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # Storage
    database_url: str = f"sqlite:///{DATA_DIR / 'blindcreators.sqlite'}"
    chroma_path: Path = DATA_DIR / "chroma"

    # HTTP
    cors_origins: list[str] = ["http://localhost:3000"]
    http_timeout_s: float = 20.0

    # Auth: the Next.js server signs short-lived HS256 JWTs with this shared secret.
    backend_jwt_secret: str = Field(default="", repr=False)
    jwt_issuer: str = "blindcreators-web"
    jwt_audience: str = "blindcreators-api"

    # Gemini
    gemini_api_key: str = Field(default="", repr=False)
    gemini_model: str = "gemini-2.5-flash"
    embed_model: str = "gemini-embedding-001"
    embed_dims: int = 768

    # Sync behaviour
    max_videos: int = 500
    max_comments_per_video: int = 200
    retention_refresh_days: int = 7
    transcripts_enabled: bool = True

    # Analytics
    min_views_for_retention: int = 1000
    hook_seconds: float = 3.0

    # AI rate limit (per user)
    ai_requests_per_window: int = 30
    ai_window_seconds: int = 600

    enable_debug_routes: bool = False

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def validate_runtime(self) -> None:
        """Fail fast on insecure configuration."""
        if len(self.backend_jwt_secret) < 32:
            raise RuntimeError(
                "BACKEND_JWT_SECRET must be set to a random string of at least 32 characters "
                "(generate one with `openssl rand -base64 48`)."
            )
        if self.environment == "production" and self.enable_debug_routes:
            raise RuntimeError("ENABLE_DEBUG_ROUTES must be false in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
