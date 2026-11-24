from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.config import Settings, get_settings
from app.db import get_db
from app.ratelimit import ai_rate_limit
from app.services import ai, rag

router = APIRouter(prefix="/api/v1/ai", tags=["ai"], dependencies=[Depends(ai_rate_limit)])


class TitleRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    preferences: str | None = Field(default=None, max_length=400)
    short: bool = True


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=6, ge=1, le=12)


@router.post("/titles")
def titles(req: TitleRequest, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    return ai.title_ideas(db, user, req.topic, req.preferences, req.short).model_dump()


@router.post("/audience-insights")
def audience(user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    result = ai.audience_insights(db, user)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No comments synced yet. Run a sync first.")
    return result.model_dump()


@router.post("/ask")
def ask(req: AskRequest, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    return rag.answer(db, user, req.question, req.top_k)


@router.post("/videos/{youtube_id}/hook-review")
def hook_review(
    youtube_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    result = ai.hook_review(db, user, youtube_id, settings)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return result.model_dump()
