"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.clients.gemini import AIRateLimited, AIUnavailable
from app.config import get_settings
from app.db import get_db
from app.migrations import upgrade_to_head
from app.models import Comment, RetentionPoint, TranscriptSegment, Video
from app.routers import account, ai, analytics
from app.services.sync import sweep_stale_jobs

logger = logging.getLogger("blindcreators")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.validate_runtime()
    upgrade_to_head()
    swept = sweep_stale_jobs()
    if swept:
        logger.warning("Marked %d stale sync job(s) as interrupted", swept)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = FastAPI(
        title="BlindCreators API",
        version="3.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Google-Access-Token"],
    )

    @app.exception_handler(AIUnavailable)
    async def _ai_unavailable(_req: Request, exc: AIUnavailable) -> JSONResponse:
        code = 429 if isinstance(exc, AIRateLimited) else 503
        return JSONResponse(status_code=code, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def _unhandled(req: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", req.method, req.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/api/v1/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "version": app.version}

    app.include_router(account.router)
    app.include_router(analytics.router)
    app.include_router(ai.router)

    if settings.enable_debug_routes:

        @app.get("/api/v1/debug/stats", tags=["debug"])
        def debug_stats(user: CurrentUser, db: Session = Depends(get_db)) -> dict:
            """Row counts for the *authenticated* user only."""
            vids = select(Video.id).where(Video.user_id == user.id)
            return {
                "videos": db.scalar(select(func.count()).select_from(Video).where(Video.user_id == user.id)),
                "retention_points": db.scalar(select(func.count()).where(RetentionPoint.video_id.in_(vids))),
                "segments": db.scalar(select(func.count()).where(TranscriptSegment.video_id.in_(vids))),
                "comments": db.scalar(select(func.count()).where(Comment.video_id.in_(vids))),
            }

    return app


app = create_app()
