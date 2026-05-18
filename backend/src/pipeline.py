import logging
import sqlite3
import uuid
import os
from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.database import (
    SyncJob,
    VideoComment,
    VideoTranscriptChunk,
    SessionLocal,
)
from src.extractors.transcripts import extract_transcript
from src.extractors.comments import extract_comments
from src.extractors.retention import extract_retention
from src.extractors.thumbnails import analyze_thumbnail
from src.rag.chroma_client import upsert_chunks, reset_collection
from src.rag.embedder import embed_batch

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "database.sqlite")

EMBED_BATCH = 50


def _get_user_videos(user_email: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT video_id, title, thumbnail_url FROM videos WHERE user_email = ?",
        (user_email,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _patch_job(db: Session, job_id: str, **kwargs):
    job = db.query(SyncJob).filter_by(job_id=job_id).first()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.commit()


def create_sync_job(user_email: str) -> str:
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        db.add(
            SyncJob(
                job_id=job_id,
                user_email=user_email,
                status="pending",
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
        return job_id
    finally:
        db.close()


def _build_comment_docs(db, user_email: str, video_titles: dict) -> list[dict]:
    """
    Groups the top 30 top-level comments per video into a single ChromaDB document each.
    Returns a list of dicts ready for upsert (without embeddings — caller adds those).
    """
    video_ids = [row[0] for row in db.query(VideoComment.video_id)
                 .filter_by(user_email=user_email, is_reply=False)
                 .distinct().all()]

    docs = []
    for vid in video_ids:
        comments = (
            db.query(VideoComment)
            .filter_by(video_id=vid, user_email=user_email, is_reply=False)
            .order_by(VideoComment.likes.desc())
            .limit(30)
            .all()
        )
        if not comments:
            continue
        title = video_titles.get(vid, vid)
        lines = [f'- {c.author}: "{c.text}" ({c.likes} likes)' for c in comments]
        document = f'Viewer comments on "{title}":\n' + "\n".join(lines)
        docs.append({
            "id": f"{user_email}::comment_block::{vid}",
            "document": document,
            "metadata": {
                "user_email": user_email,
                "video_id": vid,
                "type": "comment",
                "video_title": title,
                "start_sec": 0.0,
                "end_sec": 0.0,
            },
        })
    return docs


def run_extended_pipeline(job_id: str, access_token: str, user_email: str):
    """
    Background task: all extraction phases in sequence.
    Each extractor creates and manages its own DB session.
    The pipeline session is only used for job-status updates.
    """
    db = SessionLocal()
    try:
        _patch_job(db, job_id, status="running", current_phase="loading_videos")

        videos = _get_user_videos(user_email)
        total = len(videos)

        if not videos:
            _patch_job(
                db, job_id,
                status="done", current_phase="complete",
                videos_total=0, completed_at=datetime.utcnow(),
            )
            return

        _patch_job(db, job_id, videos_total=total)
        logger.info("Extended pipeline started for %s — %d videos", user_email, total)

        # ── Phase 1: Thumbnails ───────────────────────────────────────────
        _patch_job(db, job_id, current_phase="thumbnails", videos_done=0)
        for i, v in enumerate(videos):
            if v.get("thumbnail_url"):
                analyze_thumbnail(v["video_id"], user_email, v["thumbnail_url"])
            _patch_job(db, job_id, videos_done=i + 1)

        # ── Phase 2: Transcripts ─────────────────────────────────────────
        _patch_job(db, job_id, current_phase="transcripts", videos_done=0)
        transcript_stats: Counter = Counter()
        for i, v in enumerate(videos):
            result = extract_transcript(v["video_id"], user_email)
            transcript_stats[result["status"]] += 1
            _patch_job(db, job_id, videos_done=i + 1)
        logger.info("Transcripts done — %s", dict(transcript_stats))

        # ── Phase 3: Comments ────────────────────────────────────────────
        _patch_job(db, job_id, current_phase="comments", videos_done=0)
        comment_stats: Counter = Counter()
        for i, v in enumerate(videos):
            result = extract_comments(v["video_id"], user_email, access_token)
            comment_stats[result["status"]] += 1
            if result["status"] == "token_expired":
                logger.warning("Access token expired — stopping comments phase")
                break
            _patch_job(db, job_id, videos_done=i + 1)
        logger.info("Comments done — %s", dict(comment_stats))

        # ── Phase 4: Retention ───────────────────────────────────────────
        _patch_job(db, job_id, current_phase="retention", videos_done=0)
        retention_stats: Counter = Counter()
        for i, v in enumerate(videos):
            result = extract_retention(v["video_id"], user_email, access_token)
            retention_stats[result["status"]] += 1
            if result["status"] == "token_expired":
                logger.warning("Access token expired — stopping retention phase")
                break
            _patch_job(db, job_id, videos_done=i + 1)
        logger.info("Retention done — %s", dict(retention_stats))

        # ── Phase 5: Embeddings → ChromaDB ───────────────────────────────
        _patch_job(db, job_id, current_phase="embeddings", videos_done=0)

        # Reset entire collection — safe because all users will be re-indexed on their next sync
        reset_collection()

        video_titles = {v["video_id"]: v.get("title", "") for v in videos}
        chunk_db = SessionLocal()
        try:
            # 5a: Transcript chunks
            chunks = (
                chunk_db.query(VideoTranscriptChunk)
                .filter_by(user_email=user_email)
                .all()
            )

            if chunks:
                for batch_start in range(0, len(chunks), EMBED_BATCH):
                    batch = chunks[batch_start: batch_start + EMBED_BATCH]
                    texts = [c.chunk_text for c in batch]
                    embeddings = embed_batch(texts)

                    chroma_docs = [
                        {
                            "id": f"{user_email}::{c.video_id}::chunk_{c.chunk_index}",
                            "embedding": emb,
                            "document": c.chunk_text,
                            "metadata": {
                                "user_email": user_email,
                                "video_id": c.video_id,
                                "type": "transcript",
                                "start_sec": float(c.start_sec or 0),
                                "end_sec": float(c.end_sec or 0),
                                "video_title": video_titles.get(c.video_id, ""),
                            },
                        }
                        for c, emb in zip(batch, embeddings)
                    ]
                    upsert_chunks(chroma_docs)
                    _patch_job(
                        db, job_id,
                        videos_done=min(batch_start + EMBED_BATCH, len(chunks))
                    )
                logger.info("Indexed %d transcript chunks into ChromaDB", len(chunks))
            else:
                logger.warning("No transcript chunks to embed for %s", user_email)

            # 5b: Comment blocks (top 30 comments per video grouped into one document)
            comment_docs = _build_comment_docs(chunk_db, user_email, video_titles)
            if comment_docs:
                for batch_start in range(0, len(comment_docs), EMBED_BATCH):
                    batch = comment_docs[batch_start: batch_start + EMBED_BATCH]
                    embeddings = embed_batch([d["document"] for d in batch])
                    for doc, emb in zip(batch, embeddings):
                        doc["embedding"] = emb
                    upsert_chunks(batch)
                logger.info("Indexed %d comment blocks into ChromaDB", len(comment_docs))
            else:
                logger.info("No comments to embed for %s", user_email)
        finally:
            chunk_db.close()

        _patch_job(
            db, job_id,
            status="done",
            current_phase="complete",
            videos_done=total,
            completed_at=datetime.utcnow(),
        )
        logger.info("Extended sync complete for %s (%d videos)", user_email, total)

    except Exception as exc:
        logger.exception("Pipeline failed for %s", user_email)
        _patch_job(
            db, job_id,
            status="failed",
            error_msg=str(exc),
            completed_at=datetime.utcnow(),
        )
    finally:
        db.close()
