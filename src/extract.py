import os
import json
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_youtube_client():
    """Initializes and returns the YouTube API client."""
    return build("youtube", "v3", developerKey=API_KEY)


def get_channel_info_by_handle(youtube, handle):
    """
    Fetches the Channel ID and the 'Uploads' Playlist ID using a @handle.
    """
    # Ensure the handle starts with '@'
    clean_handle = handle if handle.startswith('@') else f'@{handle}'

    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        forHandle=clean_handle
    )
    response = request.execute()

    if not response.get('items'):
        raise ValueError(f"Channel {clean_handle} not found. Check the handle.")

    channel_data = response['items'][0]

    # Extract key data
    channel_id = channel_data['id']
    channel_name = channel_data['snippet']['title']

    # The master key to get all videos
    uploads_playlist_id = channel_data['contentDetails']['relatedPlaylists']['uploads']

    return channel_id, channel_name, uploads_playlist_id


def get_all_videos_from_playlist(youtube, playlist_id):
    """
    Retrieves all video metadata from a playlist using API pagination.
    """
    videos = []
    next_page_token = None

    # Infinite loop to handle pagination until no pages are left
    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,  # Max allowed by YouTube API
            pageToken=next_page_token
        )
        response = request.execute()

        # Iterate through the videos in the current page
        for item in response.get('items', []):
            videos.append({
                'video_id': item['contentDetails']['videoId'],
                'title': item['snippet']['title'],
                'published_at': item['snippet']['publishedAt']
            })

        # Check if there is a next page
        next_page_token = response.get('nextPageToken')

        # Exit loop if no more pages
        if not next_page_token:
            break

    return videos

def save_to_json(data, filepath):
    """
    Saves data to a JSON file, creating directories if they don't exist.
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        # indent=4 makes it readable for humans
        # ensure_ascii=False keeps emojis and special characters intact
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"📁 Data successfully saved to {filepath}")

if __name__ == "__main__":
    youtube = get_youtube_client()

    # Dogfooding with your channel
    my_handle = "@TheEldenTips"

    print(f"Searching for channel: {my_handle}...\n")

    try:
        ch_id, ch_name, uploads_id = get_channel_info_by_handle(youtube, my_handle)
        print(f"✅ Data found for channel: {ch_name}.")
        print(f"Extracting video list from playlist: {uploads_id}...\n")

        # Call our paginated function
        all_videos = get_all_videos_from_playlist(youtube, uploads_id)

        print(f"🎉 Success! Extracted a total of {len(all_videos)} videos.")

        # Display the first 3 videos as a test
        print("\nFirst 3 videos found:")
        for video in all_videos[:3]:
            print(f"- {video['title']} (ID: {video['video_id']})")

            # SAVE THE DATA
            output_path = "../data/raw/eldentips_raw_videos.json"
            save_to_json(all_videos, output_path)

    except Exception as e:
        print(f"❌ Error: {e}")