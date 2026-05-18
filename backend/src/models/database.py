from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    Float, Text, DateTime, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "database.sqlite")

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

with engine.connect() as _conn:
    _conn.execute(text("PRAGMA journal_mode=WAL"))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class VideoTranscript(Base):
    __tablename__ = "video_transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    language = Column(String, default="auto")
    is_generated = Column(Boolean, default=True)
    full_text = Column(Text)
    word_count = Column(Integer, default=0)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class VideoTranscriptChunk(Base):
    __tablename__ = "video_transcript_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    start_sec = Column(Float, default=0.0)
    end_sec = Column(Float, default=0.0)
    chunk_index = Column(Integer, default=0)


class VideoComment(Base):
    __tablename__ = "video_comments"

    comment_id = Column(String, primary_key=True)
    video_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    author = Column(String)
    text = Column(Text)
    likes = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    reply_count = Column(Integer, default=0)
    is_reply = Column(Boolean, default=False)
    parent_id = Column(String, nullable=True)


class VideoRetention(Base):
    __tablename__ = "video_retention"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, nullable=False, index=True)
    user_email = Column(String, nullable=False, index=True)
    elapsed_ratio = Column(Float)
    watch_ratio = Column(Float)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    job_id = Column(String, primary_key=True)
    user_email = Column(String, nullable=False, index=True)
    status = Column(String, default="pending")   # pending|running|done|failed
    current_phase = Column(String, default="")
    videos_total = Column(Integer, default=0)
    videos_done = Column(Integer, default=0)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


def init_db():
    """Create all new tables (does NOT touch existing tables)."""
    Base.metadata.create_all(engine, checkfirst=True)
