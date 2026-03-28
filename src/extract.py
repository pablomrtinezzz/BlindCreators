import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_youtube_client():
    """Initializes the YouTube API client."""
    return build("youtube", "v3", developerKey=API_KEY)


def get_channel_info_by_handle(youtube, handle):
    """
    Fetches the Channel ID and the 'Uploads' Playlist ID using a @handle.
    """
    clean_handle = handle if handle.startswith('@') else f'@{handle}'

    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        forHandle=clean_handle
    )
    response = request.execute()

    if not response.get('items'):
        raise ValueError(f"Channel {clean_handle} not found. Check the handle.")

    channel_data = response['items'][0]

    channel_id = channel_data['id']
    channel_name = channel_data['snippet']['title']

    uploads_playlist_id = channel_data['contentDetails']['relatedPlaylists']['uploads']

    return channel_id, channel_name, uploads_playlist_id


if __name__ == "__main__":
    youtube = get_youtube_client()

    my_handle = "@TheEldenTips"

    print(f"Searching for channel: {my_handle}...\n")

    try:
        ch_id, ch_name, uploads_id = get_channel_info_by_handle(youtube, my_handle)
        print(f"✅ Success! Data found:")
        print(f"- Channel Name: {ch_name}")
        print(f"- Channel ID: {ch_id}")
        print(f"- Uploads Playlist ID: {uploads_id}")
    except Exception as e:
        print(f"❌ Error: {e}")