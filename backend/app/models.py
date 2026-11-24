"""ORM models. Every tenant-owned row hangs off `users.id` (never off a client-supplied email)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, utcnow

ACTIVE_JOB_STATUSES = ("pending", "running")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    image: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    channel_id: Mapped[str | None] = mapped_column(String(64))
    channel_title: Mapped[str | None] = mapped_column(String(200))
    channel_thumbnail: Mapped[str | None] = mapped_column(String(500))
    subscribers: Mapped[int | None] = mapped_column(Integer)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)

    videos: Mapped[list[Video]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("user_id", "youtube_id", name="uq_video_user_youtube"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    youtube_id: Mapped[str] = mapped_column(String(32))

    title: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    is_short: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))

    # Public statistics (Data API)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Owner analytics (Analytics API, lifetime)
    avg_view_pct: Mapped[float | None] = mapped_column(Float)
    avg_view_duration_s: Mapped[float | None] = mapped_column(Float)
    watch_minutes: Mapped[float | None] = mapped_column(Float)
    subscribers_gained: Mapped[int | None] = mapped_column(Integer)
    engaged_views: Mapped[int | None] = mapped_column(Integer)
    analytics_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Retention snapshot metadata
    retention_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
    retention_views: Mapped[int | None] = mapped_column(Integer)

    # Transcript
    transcript_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|ok|none|error
    transcript_language: Mapped[str | None] = mapped_column(String(16))
    transcript_is_generated: Mapped[bool | None] = mapped_column(Boolean)

    # Comments
    comments_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)
    comments_count_at_fetch: Mapped[int | None] = mapped_column(Integer)

    # Thumbnail features
    thumb_brightness: Mapped[float | None] = mapped_column(Float)
    thumb_colors: Mapped[str | None] = mapped_column(String(200))  # comma separated hex

    synced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="videos")
    retention: Mapped[list[RetentionPoint]] = relationship(
        cascade="all, delete-orphan", order_by="RetentionPoint.elapsed_ratio"
    )
    segments: Mapped[list[TranscriptSegment]] = relationship(
        cascade="all, delete-orphan", order_by="TranscriptSegment.idx"
    )
    comments: Mapped[list[Comment]] = relationship(cascade="all, delete-orphan")


class RetentionPoint(Base):
    __tablename__ = "retention_points"
    __table_args__ = (UniqueConstraint("video_id", "elapsed_ratio", name="uq_retention_point"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    elapsed_ratio: Mapped[float] = mapped_column(Float)
    watch_ratio: Mapped[float] = mapped_column(Float)
    relative_performance: Mapped[float | None] = mapped_column(Float)


class TranscriptSegment(Base):
    """A sentence-like span of the spoken script with its timing."""

    __tablename__ = "transcript_segments"
    __table_args__ = (UniqueConstraint("video_id", "idx", name="uq_segment_idx"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    start_sec: Mapped[float] = mapped_column(Float)
    end_sec: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("video_id", "youtube_comment_id", name="uq_comment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    youtube_comment_id: Mapped[str] = mapped_column(String(64))
    parent_youtube_id: Mapped[str | None] = mapped_column(String(64))
    author: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    likes: Mapped[int] = mapped_column(Integer, default=0, index=True)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    is_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class SyncJob(Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        # At most one active job per user (DB-level backstop for the API check).
        Index(
            "uq_active_job_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'running')"),
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # pending | running | done | partial | failed | interrupted
    status: Mapped[str] = mapped_column(String(16), default="pending")
    phase: Mapped[str] = mapped_column(String(32), default="queued")
    done: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
