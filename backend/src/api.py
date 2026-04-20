from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import os

app = FastAPI(title="BlindCreators API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "database.sqlite")

def execute_query(query: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "message": "Backend FastAPI 100% Operativo"}

@app.get("/api/v1/metrics/overview")
def get_kpis():
    query = "SELECT views, likes, comments, duration_sec FROM videos"
    data = execute_query(query)
    
    if not data:
        return {"total_videos": 0, "total_views": 0, "avg_engagement": 0, "avg_duration_min": 0}
        
    df = pd.DataFrame(data)
    df['views_safe'] = df['views'].replace(0, 1)
    df['engagement_rate'] = (df['likes'] / df['views_safe']) * 100
    
    return {
        "total_videos": len(df),
        "total_views": int(df['views'].sum()),
        "avg_engagement": round(float(df['engagement_rate'].mean()), 2),
        "avg_duration_min": round(float(df['duration_sec'].mean() / 60), 1)
    }

@app.get("/api/v1/videos/top")
def get_hall_of_fame():
    query = "SELECT video_id, title, views, likes, thumbnail_url, duration_sec FROM videos ORDER BY views DESC LIMIT 5"
    data = execute_query(query)
    
    for row in data:
        mins = int(row['duration_sec'] // 60)
        secs = int(row['duration_sec'] % 60)
        row['formatted_duration'] = f"{mins}:{secs:02d}"
        
    return {"data": data}


@app.get("/api/v1/metrics/heatmap")
def get_heatmap_data():
    """Returns aggregated timing data, filtering outliers for readability."""
    query = "SELECT publish_day_name, publish_time, views FROM videos"
    data = execute_query(query)
    
    if not data:
        return {"data": []}
        
    df = pd.DataFrame(data)
    
    # 1. Clean the hour data
    df['publish_hour'] = df['publish_time'].str.split(':').str[0].astype(int)
    
    # 2. Filter outliers (Remove the top 5% most viral videos to see the real daily trend)
    threshold = df['views'].quantile(0.95)
    df_filtered = df[df['views'] < threshold]
    
    # 3. Group by day and hour using the mean of the normalized data
    heatmap_data = df_filtered.groupby(['publish_day_name', 'publish_hour'])['views'].mean().reset_index()
    
    # 4. Sort logically by day of the week, not alphabetically
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Create a sorting key
    heatmap_data['day_rank'] = heatmap_data['publish_day_name'].apply(
        lambda x: days_order.index(x) if x in days_order else 99
    )
    
    heatmap_data = heatmap_data.sort_values(['day_rank', 'publish_hour'])
    
    # Format the data for React
    result = []
    for _, row in heatmap_data.iterrows():
        result.append({
            "publish_day_name": row['publish_day_name'],
            "publish_hour": int(row['publish_hour']),
            "views": int(row['views'])
        })
        
    return {"data": result}