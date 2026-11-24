from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.config import Settings, get_settings
from app.db import get_db
from app.models import Comment, Video
from app.services import insights

router = APIRouter(prefix="/api/v1", tags=["analytics"])


@router.get("/dashboard")
def dashboard(
    user: CurrentUser, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    return insights.dashboard(db, user, settings)


@router.get("/videos")
def videos(
    user: CurrentUser,
    kind: Literal["all", "short", "long"] = "all",
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    rows = insights.list_videos(db, user, settings, kind)
    return {"videos": rows, "medians": insights.channel_medians(rows)}


@router.get("/videos/{youtube_id}")
def video(
    youtube_id: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    detail = insights.video_detail(db, user, youtube_id, settings)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return detail


@router.get("/videos/{youtube_id}/comments")
def video_comments(
    youtube_id: str, user: CurrentUser, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)
) -> dict:
    v = db.scalar(select(Video).where(Video.user_id == user.id, Video.youtube_id == youtube_id))
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    rows = db.scalars(
        select(Comment)
        .where(Comment.video_id == v.id, Comment.is_reply.is_(False))
        .order_by(Comment.likes.desc())
        .limit(limit)
    ).all()
    return {"comments": [_comment(c) for c in rows], "total": v.comment_count}


@router.get("/comments/top")
def top_comments(
    user: CurrentUser,
    limit: int = Query(100, ge=1, le=300),
    q: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    stmt = (
        select(Comment, Video.youtube_id, Video.title)
        .join(Video, Video.id == Comment.video_id)
        .where(Video.user_id == user.id, Comment.is_reply.is_(False))
    )
    if q:
        stmt = stmt.where(Comment.text.ilike(f"%{q[:100]}%"))
    rows = db.execute(stmt.order_by(Comment.likes.desc()).limit(limit)).all()
    total = (
        db.query(Comment).join(Video, Video.id == Comment.video_id).filter(Video.user_id == user.id).count()
    )
    return {
        "total": total,
        "comments": [_comment(c) | {"video_id": vid, "video_title": title} for c, vid, title in rows],
    }


@router.get("/shorts/lab")
def shorts_lab(
    user: CurrentUser, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    return insights.shorts_lab(db, user, settings)


def _comment(c: Comment) -> dict:
    return {
        "id": c.youtube_comment_id,
        "author": c.author,
        "text": c.text,
        "likes": c.likes,
        "reply_count": c.reply_count,
        "published_at": c.published_at.isoformat() if c.published_at else None,
    }
