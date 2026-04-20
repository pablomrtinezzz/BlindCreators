import os
import json
import sqlite3
import pandas as pd
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_youtube_client():
    """Initializes the YouTube API client."""
    return build("youtube", "v3", developerKey=API_KEY)


def get_top_videos_from_db(db_path="../data/database.sqlite", limit=15):
    """Fetches the video IDs of the most viewed videos from our local database."""
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT video_id, title FROM videos ORDER BY views DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return pd.DataFrame()


def extract_top_comments(youtube, video_id, max_results=20):
    """
    Fetches the top 'relevant' comments for a specific video ID.
    Ignores replies to keep the dataset focused on top-level opinions.
    """
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order="relevance",  # We want the most liked/engaged comments, not just the newest
            textFormat="plainText"
        )
        response = request.execute()

        for item in response.get("items", []):
            top_level_comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(top_level_comment)

    except Exception as e:
        # Some videos might have comments disabled, we catch the error and skip
        print(f"  ⚠️ Could not fetch comments for video {video_id}: {e}")

    return comments


def save_comments_to_json(data, filepath):
    """Saves the extracted comments to a JSON file in the raw data folder."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"\n📁 Successfully saved extracted comments to {filepath}")


if __name__ == "__main__":
    print("⛏️ Starting Audience Miner Extraction Pipeline...\n")

    youtube = get_youtube_client()
    output_path = "../data/raw/audience_comments.json"

    # 1. Read our database to know which videos to mine
    print("📊 Finding top videos to analyze...")
    top_videos_df = get_top_videos_from_db()

    if top_videos_df.empty:
        print("❌ No videos found in database. Exiting.")
        exit()

    all_extracted_data = []

    # 2. Extract comments for each video
    for index, row in top_videos_df.iterrows():
        video_id = row['video_id']
        title = row['title']

        print(f"⏳ Mining comments from: '{title}'...")
        video_comments = extract_top_comments(youtube, video_id)

        if video_comments:
            all_extracted_data.append({
                "video_id": video_id,
                "video_title": title,
                "comments": video_comments
            })
            print(f"   ✅ Extracted {len(video_comments)} top comments.")

    # 3. Save to data lake
    save_comments_to_json(all_extracted_data, output_path)
    print("\n🎉 Extraction complete! We now have the voice of the audience.")