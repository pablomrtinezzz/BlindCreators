"""Incremental, resumable channel sync.

Design:
* Each phase only processes what is missing or stale, and commits per video. Re-running a
  job after a crash or an expired token resumes where the previous one stopped.
* Videos are upserted by (user_id, youtube_id); nothing is wiped before new data arrives.
* At most one active job per user (API check + partial unique index).
* An expired Google token ends the job as `partial` (data fetched so far is kept).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, timedelta
from io import BytesIO
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageStat
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clients import captions as captions_client
from app.clients.youtube import (
    YouTubeAuthError,
    YouTubeClient,
    YouTubeError,
    YouTubeForbidden,
    parse_iso8601_duration,
)
from app.config import Settings, get_settings
from app.db import SessionLocal, utcnow
from app.models import ACTIVE_JOB_STATUSES, Comment, RetentionPoint, SyncJob, TranscriptSegment, User, Video
from app.services import rag
from app.services.text import build_segments

logger = logging.getLogger(__name__)

PHASES = ("channel", "videos", "analytics", "retention", "transcripts", "comments", "thumbnails", "index")
THUMB_HOSTS = {"i.ytimg.com", "i9.ytimg.com", "yt3.ggpht.com", "yt3.googleusercontent.com"}
MAX_THUMB_BYTES = 2_000_000


class SyncConflict(Exception):
    pass


# ── job bookkeeping ──────────────────────────────────────────────────────────


def create_job(db: Session, user: User) -> SyncJob:
    active = db.scalar(
        select(SyncJob).where(SyncJob.user_id == user.id, SyncJob.status.in_(ACTIVE_JOB_STATUSES))
    )
    if active:
        raise SyncConflict(active.id)
    job = SyncJob(id=str(uuid.uuid4()), user_id=user.id, status="pending", phase="queued")
    db.add(job)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SyncConflict("active job exists") from exc
    return job


def sweep_stale_jobs() -> int:
    """Called at startup: jobs left running by a previous process can never finish."""
    with SessionLocal() as db:
        jobs = db.scalars(select(SyncJob).where(SyncJob.status.in_(ACTIVE_JOB_STATUSES))).all()
        for job in jobs:
            job.status = "interrupted"
            job.message = "The server restarted during this sync. Run it again to resume."
            job.finished_at = utcnow()
        db.commit()
        return len(jobs)


class _Progress:
    def __init__(self, db: Session, job: SyncJob):
        self.db, self.job = db, job
        self.stats: dict[str, Counter] = {}

    def phase(self, name: str, total: int) -> None:
        self.job.phase, self.job.total, self.job.done = name, total, 0
        self.db.commit()

    def tick(self, key: str | None = None, n: int = 1) -> None:
        self.job.done = min(self.job.done + n, self.job.total) if self.job.total else self.job.done
        if key:
            self.stats.setdefault(self.job.phase, Counter())[key] += 1
        self.job.stats = json.dumps({k: dict(v) for k, v in self.stats.items()})
        self.db.commit()


# ── entry point ──────────────────────────────────────────────────────────────


def run_sync(
    job_id: str,
    access_token: str,
    *,
    client_factory: Callable[[str], YouTubeClient] | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    factory = client_factory or (lambda tok: YouTubeClient(tok, timeout=settings.http_timeout_s))
    db = SessionLocal()
    job = db.get(SyncJob, job_id)
    if job is None:
        db.close()
        return
    user = db.get(User, job.user_id)
    assert user is not None
    job.status, job.started_at = "running", utcnow()
    db.commit()
    progress = _Progress(db, job)
    yt = factory(access_token)
    try:
        uploads = _sync_channel(db, user, yt, progress)
        _sync_videos(db, user, yt, progress, settings, uploads)
        _sync_analytics(db, user, yt, progress)
        _sync_retention(db, user, yt, progress, settings)
        if settings.transcripts_enabled:
            _sync_transcripts(db, user, progress)
        _sync_comments(db, user, yt, progress, settings)
        _sync_thumbnails(db, user, progress)
        _index(db, user, progress)
        job.status, job.phase, job.message = "done", "complete", None
        user.last_synced_at = utcnow()
    except YouTubeAuthError:
        db.rollback()
        job.status = "partial"
        job.message = "Your Google session expired during the sync. Data fetched so far was kept; run it again to resume."
    except _NoChannel:
        db.rollback()
        job.status, job.message = "failed", "This Google account has no YouTube channel."
    except Exception:
        logger.exception("Sync %s failed", job_id)
        db.rollback()
        job.status, job.message = "failed", "The sync failed unexpectedly. Check the server logs and retry."
    finally:
        job.finished_at = utcnow()
        db.commit()
        db.close()
        yt.close()


class _NoChannel(Exception):
    pass


# ── phases ───────────────────────────────────────────────────────────────────


def _sync_channel(db: Session, user: User, yt: YouTubeClient, p: _Progress) -> str:
    p.phase("channel", 1)
    channel = yt.get_my_channel()
    if channel is None:
        raise _NoChannel
    user.channel_id = channel.id
    user.channel_title = channel.title
    user.channel_thumbnail = channel.thumbnail
    user.subscribers = channel.subscribers
    p.tick()
    return channel.uploads_playlist


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _looks_like_short(item: dict, duration: int) -> bool:
    if duration <= 0 or duration > 180:
        return False
    text = (
        item.get("snippet", {}).get("title", "") + " " + item.get("snippet", {}).get("description", "")
    ).lower()
    return duration <= 60 or "#shorts" in text or "#short" in text


def _sync_videos(
    db: Session, user: User, yt: YouTubeClient, p: _Progress, settings: Settings, uploads_playlist: str
) -> None:
    ids = yt.list_upload_ids(uploads_playlist, settings.max_videos)
    items = yt.get_videos(ids)
    p.phase("videos", len(items))
    existing = {v.youtube_id: v for v in db.scalars(select(Video).where(Video.user_id == user.id))}

    for item in items:
        sn, st, cd = item.get("snippet", {}), item.get("statistics", {}), item.get("contentDetails", {})
        v = existing.get(item["id"])
        if v is None:
            v = Video(user_id=user.id, youtube_id=item["id"])
            db.add(v)
            existing[item["id"]] = v
        duration = parse_iso8601_duration(cd.get("duration"))
        thumbs = sn.get("thumbnails", {})
        v.title = sn.get("title", "")[:300]
        v.description = sn.get("description", "")
        v.tags = json.dumps(sn.get("tags", []))
        v.published_at = _parse_dt(sn.get("publishedAt"))
        v.duration_sec = duration
        v.is_short = _looks_like_short(item, duration)
        new_thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
        if new_thumb != v.thumbnail_url:
            v.thumbnail_url, v.thumb_brightness, v.thumb_colors = new_thumb, None, None
        v.views = int(st.get("viewCount", 0) or 0)
        v.likes = int(st.get("likeCount", 0) or 0)
        v.comment_count = int(st.get("commentCount", 0) or 0)
        v.synced_at = utcnow()
        p.tick("upserted")

    # Videos removed from the channel are removed here too (with their derived data).
    if ids:
        current = set(ids)
        for yid, v in existing.items():
            if yid not in current:
                db.delete(v)
                p.stats.setdefault("videos", Counter())["removed"] += 1
    db.commit()


def _sync_analytics(db: Session, user: User, yt: YouTubeClient, p: _Progress) -> None:
    videos = db.scalars(select(Video).where(Video.user_id == user.id)).all()
    p.phase("analytics", 1)
    if not videos:
        p.tick()
        return
    start = min((v.published_at for v in videos if v.published_at), default=datetime(2015, 1, 1)).date()
    end = date.today()
    try:
        metrics = yt.video_metrics(start, end)
        shorts = yt.short_video_ids(start, end)
    except YouTubeForbidden as exc:
        logger.warning("Analytics API forbidden: %s", exc.reason)
        p.tick("forbidden")
        return
    now = utcnow()
    for v in videos:
        m = metrics.get(v.youtube_id)
        if shorts is not None:
            v.is_short = v.youtube_id in shorts or (v.is_short and v.youtube_id not in metrics)
        if not m:
            continue
        v.avg_view_pct = _f(m.get("averageViewPercentage"))
        v.avg_view_duration_s = _f(m.get("averageViewDuration"))
        v.watch_minutes = _f(m.get("estimatedMinutesWatched"))
        v.subscribers_gained = _i(m.get("subscribersGained"))
        v.engaged_views = _i(m.get("engagedViews"))
        v.analytics_fetched_at = now
    db.commit()
    p.tick("ok")


def _f(x) -> float | None:
    return float(x) if x is not None else None


def _i(x) -> int | None:
    return int(x) if x is not None else None


def _sync_retention(db: Session, user: User, yt: YouTubeClient, p: _Progress, settings: Settings) -> None:
    stale_before = utcnow() - timedelta(days=settings.retention_refresh_days)
    videos = db.scalars(
        select(Video).where(
            Video.user_id == user.id,
            (Video.retention_fetched_at.is_(None)) | (Video.retention_fetched_at < stale_before),
        )
    ).all()
    p.phase("retention", len(videos))
    end = date.today()
    for v in videos:
        start = (v.published_at or datetime(2015, 1, 1)).date()
        try:
            rows = yt.retention(v.youtube_id, start, end)
        except YouTubeForbidden as exc:
            p.tick(f"forbidden:{exc.reason or 'unknown'}")
            continue
        except YouTubeAuthError:
            raise
        except YouTubeError:
            p.tick("error")
            continue
        db.execute(delete(RetentionPoint).where(RetentionPoint.video_id == v.id))
        db.add_all(
            RetentionPoint(video_id=v.id, elapsed_ratio=r, watch_ratio=w, relative_performance=rel)
            for r, w, rel in rows
        )
        v.retention_fetched_at = utcnow()
        v.retention_views = v.views
        db.commit()
        p.tick("ok" if rows else "empty")


def _sync_transcripts(db: Session, user: User, p: _Progress) -> None:
    videos = db.scalars(
        select(Video).where(Video.user_id == user.id, Video.transcript_status.in_(("pending", "error")))
    ).all()
    p.phase("transcripts", len(videos))
    for v in videos:
        try:
            caps = captions_client.fetch_captions(v.youtube_id)
        except captions_client.CaptionsBlocked:
            logger.warning("Caption requests are being blocked by YouTube; skipping the rest")
            p.stats.setdefault("transcripts", Counter())["blocked"] += 1
            break
        except Exception:
            logger.exception("Captions failed for %s", v.youtube_id)
            v.transcript_status = "error"
            db.commit()
            p.tick("error")
            continue
        db.execute(delete(TranscriptSegment).where(TranscriptSegment.video_id == v.id))
        if caps is None:
            v.transcript_status = "none"
        else:
            segs = build_segments(caps.snippets)
            db.add_all(
                TranscriptSegment(video_id=v.id, idx=s.idx, start_sec=s.start, end_sec=s.end, text=s.text)
                for s in segs
            )
            v.transcript_status = "ok"
            v.transcript_language = caps.language
            v.transcript_is_generated = caps.is_generated
        db.commit()
        p.tick(v.transcript_status)


def _sync_comments(db: Session, user: User, yt: YouTubeClient, p: _Progress, settings: Settings) -> None:
    videos = [
        v
        for v in db.scalars(select(Video).where(Video.user_id == user.id)).all()
        if v.comments_fetched_at is None or v.comments_count_at_fetch != v.comment_count
    ]
    p.phase("comments", len(videos))
    for v in videos:
        if v.comment_count == 0:
            v.comments_fetched_at, v.comments_count_at_fetch = utcnow(), 0
            db.commit()
            p.tick("empty")
            continue
        try:
            items = list(yt.iter_comments(v.youtube_id, settings.max_comments_per_video))
        except YouTubeForbidden as exc:
            v.comments_fetched_at, v.comments_count_at_fetch = utcnow(), v.comment_count
            db.commit()
            p.tick("disabled" if exc.reason == "commentsDisabled" else "forbidden")
            continue
        except YouTubeAuthError:
            raise
        except YouTubeError:
            p.tick("error")
            continue
        db.execute(delete(Comment).where(Comment.video_id == v.id))
        seen: set[str] = set()
        for c in items:
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            db.add(
                Comment(
                    video_id=v.id,
                    youtube_comment_id=c["id"],
                    parent_youtube_id=c["parent"],
                    author=c["author"],
                    text=c["text"],
                    likes=c["likes"],
                    reply_count=c["reply_count"],
                    is_reply=c["parent"] is not None,
                    published_at=_parse_dt(c["published_at"]),
                )
            )
        v.comments_fetched_at, v.comments_count_at_fetch = utcnow(), v.comment_count
        db.commit()
        p.tick("ok")


def analyze_thumbnail_bytes(data: bytes) -> tuple[float, list[str]]:
    Image.MAX_IMAGE_PIXELS = 4_000_000
    img = Image.open(BytesIO(data)).convert("RGB")
    small = img.resize((64, 64))
    brightness = round(ImageStat.Stat(small.convert("L")).mean[0], 1)
    counts: Counter = Counter()
    for n, (r, g, b) in small.getcolors(64 * 64) or []:
        counts[(r // 32 * 32, g // 32 * 32, b // 32 * 32)] += n
    colors = [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in counts.most_common(5)]
    return brightness, colors


def _sync_thumbnails(db: Session, user: User, p: _Progress) -> None:
    videos = db.scalars(
        select(Video).where(
            Video.user_id == user.id, Video.thumb_brightness.is_(None), Video.thumbnail_url.is_not(None)
        )
    ).all()
    p.phase("thumbnails", len(videos))
    with httpx.Client(timeout=10, follow_redirects=False) as http:
        for v in videos:
            url = urlparse(v.thumbnail_url or "")
            if url.scheme != "https" or url.hostname not in THUMB_HOSTS:
                p.tick("blocked_host")
                continue
            try:
                res = http.get(v.thumbnail_url or "")
                res.raise_for_status()
                if len(res.content) > MAX_THUMB_BYTES:
                    p.tick("too_large")
                    continue
                v.thumb_brightness, colors = analyze_thumbnail_bytes(res.content)
                v.thumb_colors = ",".join(colors)
                db.commit()
                p.tick("ok")
            except Exception:
                logger.warning("Thumbnail analysis failed for %s", v.youtube_id)
                p.tick("error")


def _index(db: Session, user: User, p: _Progress) -> None:
    p.phase("index", 1)
    try:
        result = rag.index_user(db, user)
        p.stats.setdefault("index", Counter()).update(result)
        p.tick("ok")
    except rag.AIUnavailable as exc:
        logger.warning("Skipping vector index: %s", exc)
        p.tick("skipped_ai_unavailable")
