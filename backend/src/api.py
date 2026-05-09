# backend/src/api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os
import requests
from pydantic import BaseModel
from src.ai_assistant import generate_seo_titles, mine_audience_insights
from src.youtube_sync import run_user_sync_pipeline

app = FastAPI(title="BlindCreators API", version="1.0")

# SECURITY: Allow only our Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "database.sqlite")


def execute_query(query: str, params=()):
    """Helper to execute SQL queries and return results as a list of dictionaries."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "message": "Backend FastAPI 100% Operativo"}


# --- AUTH & USER ENDPOINTS ---

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
            INSERT INTO users (email, name, image)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET name=excluded.name, image=excluded.image
        ''', (user.email, user.name, user.image))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- YOUTUBE DATA ENDPOINTS ---

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
                "total_views": channel["statistics"]["viewCount"]
            }
    return {"status": "error", "message": "Channel not found"}


class SyncRequest(BaseModel):
    access_token: str
    user_email: str


@app.post("/api/v1/youtube/sync")
def trigger_youtube_sync(req: SyncRequest):
    """
    Triggers the real-time sync pipeline.
    """
    try:
        print(f"🚀 Starting sync for: {req.user_email}")
        result = run_user_sync_pipeline(req.access_token, req.user_email)

        if result["status"] == "error":
            print(f"❌ Pipeline error: {result['message']}")
            raise HTTPException(status_code=400, detail=result["message"])

        return result
    except Exception as e:
        print(f"💥 Critical server error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# --- METRICS ENDPOINTS (FILTERED BY USER) ---

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
        "avg_duration_min": round(float(df['duration_sec'].mean() / 60), 1)
    }


@app.get("/api/v1/metrics/heatmap")
def get_heatmap_data(user_email: str = "eldenringhustle@gmail.com"):
    """
    ADDED: Calculates performance by day for the TimingChart.
    """
    query = "SELECT publish_day_name as day, AVG(views) as value FROM videos WHERE user_email = ? GROUP BY publish_day_name"
    try:
        data = execute_query(query, (user_email,))

        # Sort days correctly
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        data_dict = {row['day']: row['value'] for row in data}

        formatted_data = []
        for day in order:
            formatted_data.append({
                "day": day[:3],  # Mon, Tue...
                "value": int(data_dict.get(day, 0))
            })

        return {"data": formatted_data}
    except Exception as e:
        print(f"Heatmap error: {e}")
        return {"data": []}


@app.get("/api/v1/videos/top")
def get_hall_of_fame(user_email: str = "eldenringhustle@gmail.com"):
    query = "SELECT video_id, title, views, likes, thumbnail_url, duration_sec FROM videos WHERE user_email = ? ORDER BY views DESC LIMIT 5"
    data = execute_query(query, (user_email,))
    return {"data": data}


# --- AI ENDPOINTS ---

class TitleRequest(BaseModel):
    topic: str
    extra_instructions: str | None = None


@app.post("/api/v1/ai/generate-titles")
def api_generate_titles(request: TitleRequest, user_email: str = "eldenringhustle@gmail.com"):
    generated_text = generate_seo_titles(request.topic, user_email, request.extra_instructions)
    # Filter lines that start with numbers (1., 2., 3.)
    titles_list = [t.strip() for t in generated_text.split('\n') if t.strip() and t[0].isdigit()]
    return {"data": titles_list}


@app.get("/api/v1/ai/audience-insights")
def api_mine_audience():
    return {"data": mine_audience_insights()}