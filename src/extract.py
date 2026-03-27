import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")


def get_youtube_client():
    """Initializes the YouTube API client."""
    return build("youtube", "v3", developerKey=API_KEY)


def get_channel_stats(youtube, channel_id):
    """Fetches basic statistics for a given channel ID."""
    request = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id
    )
    response = request.execute()
    return response


if __name__ == "__main__":
    # Initialize client
    youtube = get_youtube_client()

    # Test with a channel (e.g., My old channel TheEldenTips: UCdA-MnyXVSMvradoJ3Ck2Zw)
    test_channel_id = "UCdA-MnyXVSMvradoJ3Ck2Zw"

    print(f"Fetching data for channel: {test_channel_id}...")
    data = get_channel_stats(youtube, test_channel_id)

    # Print the channel name and subscriber count
    channel_name = data['items'][0]['snippet']['title']
    sub_count = data['items'][0]['statistics']['subscriberCount']

    print(f"Success!")
    print(f"Channel Name: {channel_name}")
    print(f"Subscribers: {sub_count}")