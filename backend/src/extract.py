import os
import json
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_youtube_client():
    """Initializes and returns the YouTube API client."""
    return build("youtube", "v3", developerKey=API_KEY)


def get_channel_info_by_handle(youtube, handle):
    """Fetches the Channel ID and the 'Uploads' Playlist ID using a @handle."""
    clean_handle = handle if handle.startswith('@') else f'@{handle}'
    request = youtube.channels().list(part="snippet,contentDetails,statistics", forHandle=clean_handle)
    response = request.execute()

    if not response.get('items'):
        raise ValueError(f"Channel {clean_handle} not found.")

    channel_data = response['items'][0]
    return channel_data['id'], channel_data['snippet']['title'], channel_data['contentDetails']['relatedPlaylists'][
        'uploads']


def get_all_videos_from_playlist(youtube, playlist_id):
    """Retrieves basic video metadata from a playlist using API pagination."""
    videos = []
    next_page_token = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response.get('items', []):
            videos.append(item['contentDetails']['videoId'])

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return videos


def get_video_details(youtube, video_ids):
    """
    Fetches detailed statistics for a list of video IDs.
    Implements batching to handle the 50 IDs per request API limit.
    """
    all_video_stats = []

    # Batching / Chunking logic: step by 50
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]

        request = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(chunk)  # Joins the list into a comma-separated string
        )
        response = request.execute()
        all_video_stats.extend(response.get('items', []))

    return all_video_stats


def save_to_json(data, filepath):
    """Saves data to a JSON file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"📁 Data successfully saved to {filepath}")


if __name__ == "__main__":
    youtube = get_youtube_client()
    my_handle = "@TheEldenTips"

    output_path = "../data/raw/eldentips_raw_videos.json"

    print(f"🔄 Starting Data Extraction Pipeline for {my_handle}...\n")

    try:
        # 1. Get Playlist ID
        ch_id, ch_name, uploads_id = get_channel_info_by_handle(youtube, my_handle)
        print(f"✅ Found channel: {ch_name}")

        # 2. Get all Video IDs
        video_ids = get_all_videos_from_playlist(youtube, uploads_id)
        print(f"✅ Found {len(video_ids)} video IDs. Fetching detailed stats in batches...")

        # 3. Enrich with detailed stats (Batching)
        enriched_videos = get_video_details(youtube, video_ids)
        print(f"🎉 Success! Extracted rich data for {len(enriched_videos)} videos.")

        # Display the first video's views as a test
        first_video_title = enriched_videos[0]['snippet']['title']
        first_video_views = enriched_videos[0]['statistics'].get('viewCount', '0')
        print(f"\nExample -> {first_video_title} | Views: {first_video_views}")

        # 4. Save the rich data
        save_to_json(enriched_videos, output_path)

    except Exception as e:
        print(f"❌ Error: {e}")