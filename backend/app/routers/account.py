from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, google_access_token
from app.clients import vectors
from app.clients.youtube import YouTubeAuthError, YouTubeClient
from app.config import Settings, get_settings
from app.db import get_db
from app.models import SyncJob, Video
from app.services import sync as sync_service

router = APIRouter(prefix="/api/v1", tags=["account"])


def _job_out(job: SyncJob | None) -> dict | None:
    if job is None:
        return None
    return {
        "id": job.id,
        "status": job.status,
        "phase": job.phase,
        "phase_index": sync_service.PHASES.index(job.phase) if job.phase in sync_service.PHASES else None,
        "phases": list(sync_service.PHASES),
        "done": job.done,
        "total": job.total,
        "message": job.message,
        "stats": json.loads(job.stats or "{}"),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


@router.get("/me")
def me(user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    last = db.scalar(
        select(SyncJob).where(SyncJob.user_id == user.id).order_by(SyncJob.created_at.desc()).limit(1)
    )
    videos = db.query(Video).filter(Video.user_id == user.id).count()
    return {
        "email": user.email,
        "name": user.name,
        "image": user.image,
        "channel": {
            "id": user.channel_id,
            "title": user.channel_title,
            "thumbnail": user.channel_thumbnail,
            "subscribers": user.subscribers,
        },
        "videos": videos,
        "last_synced_at": user.last_synced_at.isoformat() if user.last_synced_at else None,
        "last_job": _job_out(last),
    }


@router.delete("/me/data", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_data(user: CurrentUser, db: Session = Depends(get_db)) -> None:
    """Deletes every stored video, curve, transcript, comment, job and vector for this user."""
    if db.scalar(
        select(SyncJob).where(SyncJob.user_id == user.id, SyncJob.status.in_(("pending", "running")))
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Wait for the running sync to finish first.")
    db.execute(delete(Video).where(Video.user_id == user.id))
    db.execute(delete(SyncJob).where(SyncJob.user_id == user.id))
    user.channel_id = user.channel_title = user.channel_thumbnail = None
    user.subscribers = None
    user.last_synced_at = None
    db.commit()
    vectors.delete_user_collection(user.id)


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
def start_sync(
    user: CurrentUser,
    background: BackgroundTasks,
    token: str = Depends(google_access_token),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    # Bind the Google token to the authenticated user: a token for another account is rejected.
    with YouTubeClient(token, timeout=settings.http_timeout_s) as yt:
        try:
            token_email = yt.token_email()
        except YouTubeAuthError as exc:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Google session expired. Sign in again."
            ) from exc
    if token_email != user.email:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The Google token does not belong to this account.")
    try:
        job = sync_service.create_job(db, user)
    except sync_service.SyncConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "A sync is already running for this account.") from exc
    background.add_task(sync_service.run_sync, job.id, token)
    return _job_out(job)  # type: ignore[return-value]


@router.get("/sync/jobs/latest")
def latest_job(user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    job = db.scalar(
        select(SyncJob).where(SyncJob.user_id == user.id).order_by(SyncJob.created_at.desc()).limit(1)
    )
    return {"job": _job_out(job)}


@router.get("/sync/jobs/{job_id}")
def get_job(job_id: str, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    job = db.get(SyncJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return _job_out(job)  # type: ignore[return-value]
