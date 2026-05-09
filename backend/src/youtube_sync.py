# backend/src/youtube_sync.py
import requests
import pandas as pd
import sqlite3
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "database.sqlite")

def parse_iso8601_duration(duration_str):
    """Converts YouTube's PT#M#S format to total seconds."""
    hours = re.search(r'(\d+)H', duration_str)
    minutes = re.search(r'(\d+)M', duration_str)
    seconds = re.search(r'(\d+)S', duration_str)

    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    s = int(seconds.group(1)) if seconds else 0

    return h * 3600 + m * 60 + s

def run_user_sync_pipeline(access_token: str, user_email: str):
    """
    Extracts, transforms, and loads a specific user's YouTube data into the database.
    This replaces the old manual ETL scripts for a real-time B2B architecture.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    try:
        # 1. Get Channel's Uploads Playlist
        url_channel = "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&mine=true"
        res_channel = requests.get(url_channel, headers=headers).json()
        
        if not res_channel.get("items"):
            return {"status": "error", "message": "No YouTube channel found for this user."}
            
        uploads_playlist_id = res_channel["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # 2. Extract Video IDs from Playlist (Grabbing the latest 50 videos for this MVP)
        url_playlist = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_playlist_id}&maxResults=50"
        res_playlist = requests.get(url_playlist, headers=headers).json()
        
        video_ids = [item["contentDetails"]["videoId"] for item in res_playlist.get("items", [])]
        
        if not video_ids:
            return {"status": "success", "message": "No videos found in channel.", "videos_synced": 0}

        # 3. Extract Detailed Video Stats
        ids_string = ",".join(video_ids)
        url_videos = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id={ids_string}"
        res_videos = requests.get(url_videos, headers=headers).json()
        raw_videos = res_videos.get("items", [])
        
        if not raw_videos:
             return {"status": "error", "message": "Failed to fetch video details."}

        # 4. Transform Data (Pandas)
        df = pd.json_normalize(raw_videos)
        
        golden_columns = {
            'id': 'video_id',
            'snippet.title': 'title',
            'snippet.description': 'description',
            'snippet.tags': 'tags',
            'snippet.publishedAt': 'published_at',
            'contentDetails.duration': 'duration_raw',
            'statistics.viewCount': 'views',
            'statistics.likeCount': 'likes',
            'statistics.commentCount': 'comments',
            'snippet.thumbnails.high.url': 'thumbnail_url'
        }
        
        existing_cols = {k: v for k, v in golden_columns.items() if k in df.columns}
        df = df[list(existing_cols.keys())].rename(columns=existing_cols)
        
        # VERY IMPORTANT: Tag every row with the user's email (Multi-Tenant architecture)
        df['user_email'] = user_email
        
        # Format types and clean tags
        for col in ['views', 'likes', 'comments']:
            if col in df.columns:
                df[col] = df[col].fillna(0).astype(int)
        
        if 'tags' in df.columns:
            df['tags'] = df['tags'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
            
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'])
            df['publish_day_name'] = df['published_at'].dt.day_name()
            df['publish_time'] = df['published_at'].dt.strftime('%H:%M')
            df = df.drop(columns=['published_at'])
            
        if 'duration_raw' in df.columns:
            df['duration_sec'] = df['duration_raw'].apply(parse_iso8601_duration)
            df['is_short'] = df['duration_sec'] <= 60
            df = df.drop(columns=['duration_raw'])

        # 5. Load to Database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ensure the table is ready for multi-tenant data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT,
                title TEXT,
                description TEXT,
                tags TEXT,
                views INTEGER,
                likes INTEGER,
                comments INTEGER,
                thumbnail_url TEXT,
                user_email TEXT,
                publish_day_name TEXT,
                publish_time TEXT,
                duration_sec INTEGER,
                is_short BOOLEAN
            )
        ''')
        
        # Wipe ONLY this specific user's old videos before inserting fresh ones
        cursor.execute("DELETE FROM videos WHERE user_email = ?", (user_email,))
        
        # Append the newly fetched data
        df.to_sql('videos', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "Data synchronized successfully.", "videos_synced": len(df)}

    except Exception as e:
        return {"status": "error", "message": f"Sync failed: {str(e)}"}