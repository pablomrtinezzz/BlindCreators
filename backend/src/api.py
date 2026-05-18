# backend/src/api.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os
import requests
from pydantic import BaseModel
from src.ai_assistant import generate_seo_titles, mine_audience_insights, rag_query
from src.youtube_sync import run_user_sync_pipeline
from src.models.database import (
    SyncJob, VideoTranscript, VideoTranscriptChunk,
    VideoComment, VideoRetention, SessionLocal, init_db,
)
from src.pipeline import create_sync_job, run_extended_pipeline
from src.rag.chroma_client import reset_collection
from src.rag.embedder import embed_batch

app = FastAPI(title="BlindCreators API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "database.sqlite")


@app.on_event("startup")
def startup():
    init_db()


def execute_query(query: str, params=()):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "message": "BlindCreators API v2.0 operativo"}


# ── Auth / Users ──────────────────────────────────────────────────────────────

class UserSync(BaseModel):
    email: str
    name: str
    image: str | None = None


@app.post("/api/v1/users/sync")
def sync_user(user: UserSync):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            INSERT INTO users (email, name, image) VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET name=excluded.name, image=excluded.image
        ''', (user.email, user.name, user.image))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── YouTube Channel Verify ────────────────────────────────────────────────────

class YouTubeTokenRequest(BaseModel):
    access_token: str


@app.post("/api/v1/youtube/verify-channel")
def verify_youtube_channel(req: YouTubeTokenRequest):
    headers = {"Authorization": f"Bearer {req.access_token}"}
    url = "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data.get("items"):
            channel = data["items"][0]
            return {
                "status": "success",
                "channel_name": channel["snippet"]["title"],
                "subscribers": channel["statistics"]["subscriberCount"],
                "total_views": channel["statistics"]["viewCount"],
            }
    return {"status": "error", "message": "Channel not found"}


# ── Quick Sync (legacy, still works) ─────────────────────────────────────────

class SyncRequest(BaseModel):
    access_token: str
    user_email: str


@app.post("/api/v1/youtube/sync")
def trigger_youtube_sync(req: SyncRequest):
    try:
        result = run_user_sync_pipeline(req.access_token, req.user_email)
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Extended Async Sync ───────────────────────────────────────────────────────

@app.post("/api/v1/youtube/sync-extended")
def trigger_extended_sync(req: SyncRequest, background_tasks: BackgroundTasks):
    """
    Kicks off the full extraction pipeline asynchronously.
    Returns a job_id immediately; poll /jobs/{job_id} for progress.
    """
    # First run the quick video sync synchronously so data is immediately available
    quick = run_user_sync_pipeline(req.access_token, req.user_email)
    if quick.get("status") == "error":
        raise HTTPException(status_code=400, detail=quick["message"])

    job_id = create_sync_job(req.user_email)
    background_tasks.add_task(
        run_extended_pipeline, job_id, req.access_token, req.user_email
    )

    return {
        "status": "accepted",
        "job_id": job_id,
        "videos_synced": quick.get("videos_synced", 0),
        "message": "Videos synced. Extended pipeline started in background.",
    }


# ── Job Status ────────────────────────────────────────────────────────────────

PHASE_LABELS = {
    "loading_videos": "Loading video list",
    "thumbnails": "Analyzing thumbnails",
    "transcripts": "Extracting transcripts",
    "comments": "Mining comments",
    "retention": "Fetching retention curves",
    "embeddings": "Building vector index",
    "complete": "Complete",
}


@app.get("/api/v1/jobs/{job_id}")
def get_job_status(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(SyncJob).filter_by(job_id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        progress = 0
        if job.videos_total and job.videos_total > 0:
            progress = round((job.videos_done / job.videos_total) * 100)
        return {
            "job_id": job.job_id,
            "status": job.status,
            "phase": job.current_phase,
            "phase_label": PHASE_LABELS.get(job.current_phase, job.current_phase),
            "videos_total": job.videos_total,
            "videos_done": job.videos_done,
            "progress": progress,
            "error": job.error_msg,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
    finally:
        db.close()


# ── Metrics (existing, unchanged) ────────────────────────────────────────────

@app.get("/api/v1/metrics/overview")
def get_kpis(user_email: str = "eldenringhustle@gmail.com"):
    query = "SELECT views, likes, comments, duration_sec FROM videos WHERE user_email = ?"
    data = execute_query(query, (user_email,))
    if not data:
        return {"total_videos": 0, "total_views": 0, "avg_engagement": 0, "avg_duration_min": 0}
    df = pd.DataFrame(data)
    df['engagement_rate'] = (df['likes'] / df['views'].replace(0, 1)) * 100
    return {
        "total_videos": len(df),
        "total_views": int(df['views'].sum()),
        "avg_engagement": round(float(df['engagement_rate'].mean()), 2),
        "avg_duration_min": round(float(df['duration_sec'].mean() / 60), 1),
    }


@app.get("/api/v1/metrics/heatmap")
def get_heatmap_data(user_email: str = "eldenringhustle@gmail.com"):
    query = "SELECT publish_day_name as day, AVG(views) as value FROM videos WHERE user_email = ? GROUP BY publish_day_name"
    try:
        data = execute_query(query, (user_email,))
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        data_dict = {row['day']: row['value'] for row in data}
        return {
            "data": [
                {"day": day[:3], "value": int(data_dict.get(day, 0))}
                for day in order
            ]
        }
    except Exception as e:
        print(f"Heatmap error: {e}")
        return {"data": []}


@app.get("/api/v1/videos/top")
def get_hall_of_fame(user_email: str = "eldenringhustle@gmail.com"):
    query = "SELECT video_id, title, views, likes, thumbnail_url, duration_sec FROM videos WHERE user_email = ? ORDER BY views DESC LIMIT 5"
    return {"data": execute_query(query, (user_email,))}


# ── Reindex (re-embed without full sync) ─────────────────────────────────────

class ReindexRequest(BaseModel):
    user_email: str


def _run_reindex(user_email: str):
    """Background task: re-embed all transcript chunks and comment blocks into ChromaDB."""
    from src.models.database import VideoTranscriptChunk
    from src.pipeline import _build_comment_docs
    from src.rag.chroma_client import upsert_chunks
    import sqlite3 as _sqlite3

    db = SessionLocal()
    try:
        reset_collection()

        conn = _sqlite3.connect(DB_PATH)
        conn.row_factory = _sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT video_id, title FROM videos WHERE user_email = ?", (user_email,))
        titles = {r["video_id"]: r["title"] for r in cur.fetchall()}
        conn.close()

        BATCH = 50

        # Transcript chunks
        chunks = db.query(VideoTranscriptChunk).filter_by(user_email=user_email).all()
        for i in range(0, len(chunks), BATCH):
            batch = chunks[i: i + BATCH]
            embeddings = embed_batch([c.chunk_text for c in batch])
            upsert_chunks([
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
                        "video_title": titles.get(c.video_id, ""),
                    },
                }
                for c, emb in zip(batch, embeddings)
            ])

        # Comment blocks
        comment_docs = _build_comment_docs(db, user_email, titles)
        for i in range(0, len(comment_docs), BATCH):
            batch = comment_docs[i: i + BATCH]
            embeddings = embed_batch([d["document"] for d in batch])
            for doc, emb in zip(batch, embeddings):
                doc["embedding"] = emb
            upsert_chunks(batch)
    finally:
        db.close()


@app.post("/api/v1/youtube/reindex")
def trigger_reindex(req: ReindexRequest, background_tasks: BackgroundTasks):
    """Re-embed all transcript chunks into ChromaDB without a full sync."""
    background_tasks.add_task(_run_reindex, req.user_email)
    return {"status": "accepted", "message": "Re-indexing started in background"}


# ── Transcripts ───────────────────────────────────────────────────────────────

@app.get("/api/v1/transcripts")
def list_transcripts(user_email: str):
    # Join with videos table to get titles and thumbnails
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT vt.video_id, vt.language, vt.is_generated, vt.word_count, vt.fetched_at,
               v.title, v.thumbnail_url
        FROM video_transcripts vt
        LEFT JOIN videos v ON vt.video_id = v.video_id AND v.user_email = vt.user_email
        WHERE vt.user_email = ?
        ORDER BY v.views DESC
    """, (user_email,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "data": [
            {
                "video_id": r["video_id"],
                "title": r["title"] or r["video_id"],
                "thumbnail_url": r["thumbnail_url"],
                "language": r["language"],
                "is_generated": bool(r["is_generated"]),
                "word_count": r["word_count"],
                "fetched_at": r["fetched_at"],
            }
            for r in rows
        ]
    }


@app.get("/api/v1/transcripts/{video_id}")
def get_transcript(video_id: str, user_email: str):
    db = SessionLocal()
    try:
        t = db.query(VideoTranscript).filter_by(
            video_id=video_id, user_email=user_email
        ).first()
        if not t:
            raise HTTPException(status_code=404, detail="Transcript not found")

        chunks = (
            db.query(VideoTranscriptChunk)
            .filter_by(video_id=video_id, user_email=user_email)
            .order_by(VideoTranscriptChunk.chunk_index)
            .all()
        )
        return {
            "video_id": video_id,
            "language": t.language,
            "is_generated": t.is_generated,
            "word_count": t.word_count,
            "full_text": t.full_text,
            "chunks": [
                {
                    "index": c.chunk_index,
                    "text": c.chunk_text,
                    "start_sec": c.start_sec,
                    "end_sec": c.end_sec,
                }
                for c in chunks
            ],
        }
    finally:
        db.close()


# ── Comments ──────────────────────────────────────────────────────────────────

@app.get("/api/v1/comments/{video_id}")
def get_comments(video_id: str, user_email: str, limit: int = 50):
    db = SessionLocal()
    try:
        rows = (
            db.query(VideoComment)
            .filter_by(video_id=video_id, user_email=user_email, is_reply=False)
            .order_by(VideoComment.likes.desc())
            .limit(limit)
            .all()
        )
        return {
            "data": [
                {
                    "comment_id": r.comment_id,
                    "author": r.author,
                    "text": r.text,
                    "likes": r.likes,
                    "reply_count": r.reply_count,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                }
                for r in rows
            ]
        }
    finally:
        db.close()


@app.get("/api/v1/comments/summary/{user_email}")
def get_comments_summary(user_email: str):
    """Top comments across all videos, ordered by likes."""
    db = SessionLocal()
    try:
        rows = (
            db.query(VideoComment)
            .filter_by(user_email=user_email, is_reply=False)
            .order_by(VideoComment.likes.desc())
            .limit(100)
            .all()
        )
        total = db.query(VideoComment).filter_by(user_email=user_email).count()
        return {
            "total_comments": total,
            "data": [
                {
                    "comment_id": r.comment_id,
                    "video_id": r.video_id,
                    "author": r.author,
                    "text": r.text,
                    "likes": r.likes,
                    "reply_count": r.reply_count,
                }
                for r in rows
            ],
        }
    finally:
        db.close()


# ── Retention ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/retention/{video_id}")
def get_retention(video_id: str, user_email: str):
    db = SessionLocal()
    try:
        rows = (
            db.query(VideoRetention)
            .filter_by(video_id=video_id, user_email=user_email)
            .order_by(VideoRetention.elapsed_ratio)
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="No retention data for this video")
        return {
            "video_id": video_id,
            "data": [
                {"elapsed_pct": round(r.elapsed_ratio * 100, 1), "watch_pct": round(r.watch_ratio * 100, 1)}
                for r in rows
            ],
        }
    finally:
        db.close()


@app.get("/api/v1/retention/summary/{user_email}")
def get_retention_summary(user_email: str):
    """Average retention curve across all videos for the channel."""
    db = SessionLocal()
    try:
        rows = db.query(VideoRetention).filter_by(user_email=user_email).all()
        if not rows:
            return {"data": []}

        from collections import defaultdict
        buckets: dict[float, list[float]] = defaultdict(list)
        for r in rows:
            bucket = round(r.elapsed_ratio, 2)
            buckets[bucket].append(r.watch_ratio)

        data = sorted([
            {
                "elapsed_pct": round(k * 100, 1),
                "watch_pct": round((sum(v) / len(v)) * 100, 1),
            }
            for k, v in buckets.items()
        ], key=lambda x: x["elapsed_pct"])

        return {"data": data}
    finally:
        db.close()


# ── AI ────────────────────────────────────────────────────────────────────────

class TitleRequest(BaseModel):
    topic: str
    extra_instructions: str | None = None


@app.post("/api/v1/ai/generate-titles")
def api_generate_titles(request: TitleRequest, user_email: str = "eldenringhustle@gmail.com"):
    generated_text = generate_seo_titles(request.topic, user_email, request.extra_instructions)
    titles_list = [t.strip() for t in generated_text.split('\n') if t.strip() and t[0].isdigit()]
    return {"data": titles_list}


@app.get("/api/v1/ai/audience-insights")
def api_mine_audience(user_email: str = "eldenringhustle@gmail.com"):
    return {"data": mine_audience_insights()}


# ── Debug ─────────────────────────────────────────────────────────────────────

@app.get("/api/v1/debug/stats/{user_email}")
def debug_stats(user_email: str):
    """Returns counts from all tables + ChromaDB for a user."""
    from src.rag.chroma_client import get_collection

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    def count(table, col="user_email"):
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} = ?", (user_email,))
        return cur.fetchone()[0]

    cur.execute(
        "SELECT job_id, status, current_phase, videos_total, videos_done, error_msg, created_at FROM sync_jobs WHERE user_email = ? ORDER BY created_at DESC LIMIT 1",
        (user_email,)
    )
    row = cur.fetchone()
    last_job = dict(zip(["job_id","status","phase","videos_total","videos_done","error","created_at"], row)) if row else None
    conn.close()

    try:
        col = get_collection()
        chroma_count = col.count()
        chroma_user = len(col.get(where={"user_email": user_email}).get("ids", []))
    except Exception as e:
        chroma_count = f"error: {e}"
        chroma_user = 0

    return {
        "user": user_email,
        "last_job": last_job,
        "tables": {
            "videos": count("videos"),
            "video_transcripts": count("video_transcripts"),
            "video_transcript_chunks": count("video_transcript_chunks"),
            "video_comments": count("video_comments"),
            "video_retention": count("video_retention"),
        },
        "chromadb": {
            "total_docs": chroma_count,
            "user_docs": chroma_user,
        },
    }


@app.post("/api/v1/debug/test-comments")
def test_single_video_comments(req: SyncRequest):
    """Raw YouTube commentThreads API call — returns full HTTP status + response JSON."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT video_id FROM videos WHERE user_email = ? LIMIT 1", (req.user_email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"error": "No videos found for this user"}

    video_id = row[0]
    headers = {"Authorization": f"Bearer {req.access_token}"}
    try:
        res = requests.get(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers=headers,
            params={
                "part": "snippet",
                "videoId": video_id,
                "maxResults": 5,
                "order": "relevance",
                "textFormat": "plainText",
            },
            timeout=15,
        )
        try:
            body = res.json()
        except Exception:
            body = {"raw_text": res.text[:500]}
    except Exception as e:
        return {"video_id": video_id, "error": str(e)}

    return {"video_id": video_id, "http_status": res.status_code, "response": body}


@app.post("/api/v1/debug/test-retention")
def test_single_video_retention(req: SyncRequest):
    """Raw YouTube Analytics API call — returns full HTTP status + response JSON."""
    from datetime import date as _date
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT video_id FROM videos WHERE user_email = ? LIMIT 1", (req.user_email,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"error": "No videos found for this user"}

    video_id = row[0]
    headers = {"Authorization": f"Bearer {req.access_token}"}
    try:
        res = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers=headers,
            params={
                "ids": "channel==MINE",
                "metrics": "audienceWatchRatio,relativeRetentionPerformance",
                "dimensions": "elapsedVideoTimeRatio",
                "filters": f"video=={video_id}",
                "startDate": "2020-01-01",
                "endDate": _date.today().isoformat(),
            },
            timeout=15,
        )
        try:
            body = res.json()
        except Exception:
            body = {"raw_text": res.text[:500]}
    except Exception as e:
        return {"video_id": video_id, "error": str(e)}

    return {"video_id": video_id, "http_status": res.status_code, "response": body}


class RAGRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/api/v1/ai/rag-query")
def api_rag_query(req: RAGRequest, user_email: str):
    """Semantic search over indexed transcripts with Gemini-grounded answer."""
    try:
        result = rag_query(req.query, user_email, req.top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
