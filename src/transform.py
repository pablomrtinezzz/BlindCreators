import json
import pandas as pd
import os
import re


def load_raw_data(filepath):
    """Loads raw JSON data from the specified path."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_iso8601_duration(duration_str):
    """Converts YouTube's PT#M#S format to total seconds."""
    # Search for Hours, Minutes, and Seconds using Regex
    hours = re.search(r'(\d+)H', duration_str)
    minutes = re.search(r'(\d+)M', duration_str)
    seconds = re.search(r'(\d+)S', duration_str)

    # Convert to integers if they exist, otherwise 0
    h = int(hours.group(1)) if hours else 0
    m = int(minutes.group(1)) if minutes else 0
    s = int(seconds.group(1)) if seconds else 0

    return h * 3600 + m * 60 + s


def transform_video_data(raw_data):
    """
    Cleans and transforms complex nested JSON from YouTube API.
    Extracts metrics, parses ISO durations, categorizes Shorts,
    and includes SEO metadata (tags, description).
    """
    df = pd.json_normalize(raw_data)

    # 1. Golden Columns
    golden_columns = {
        'id': 'video_id',
        'snippet.title': 'title',
        'snippet.description': 'description',  # NEW: For NLP & AI
        'snippet.tags': 'tags',  # NEW: For SEO Analysis
        'contentDetails.definition': 'definition',  # NEW: hd vs sd
        'snippet.channelTitle': 'channel_name',
        'snippet.categoryId': 'category_id',
        'snippet.publishedAt': 'published_at',
        'contentDetails.duration': 'duration_raw',
        'statistics.viewCount': 'views',
        'statistics.likeCount': 'likes',
        'statistics.commentCount': 'comments',
        'snippet.thumbnails.high.url': 'thumbnail_url'
    }

    existing_cols = {k: v for k, v in golden_columns.items() if k in df.columns}
    df = df[list(existing_cols.keys())].rename(columns=existing_cols)

    # 2. Data Type Conversions
    metrics = ['views', 'likes', 'comments']
    for col in metrics:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    # 3. Handle Lists (Tags): Convert list of tags to a comma-separated string
    if 'tags' in df.columns:
        # If a video has no tags, the API doesn't send the field or sends NaN
        df['tags'] = df['tags'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")

    # 4. Feature Engineering: Time and Dates
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'])
        df['publish_day_name'] = df['published_at'].dt.day_name()
        df['publish_time'] = df['published_at'].dt.strftime('%H:%M')
        df = df.drop(columns=['published_at'])

    # 5. Feature Engineering: Duration & Content Type
    if 'duration_raw' in df.columns:
        df['duration_sec'] = df['duration_raw'].apply(parse_iso8601_duration)
        df['is_short'] = df['duration_sec'] <= 60
        df = df.drop(columns=['duration_raw'])

    return df


def save_processed_data(df, filepath):
    """Saves the cleaned DataFrame to a CSV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False, encoding='utf-8')
    print(f"📁 Processed data saved successfully to {filepath}")


if __name__ == "__main__":
    input_path = "../data/raw/eldentips_raw_videos.json"
    output_path = "../data/processed/eldentips_cleaned_videos.csv"

    print("🔄 Starting Data Transformation Pipeline...")

    try:
        raw_videos = load_raw_data(input_path)
        clean_df = transform_video_data(raw_videos)

        print(f"✅ Data transformed. Total videos: {clean_df.shape[0]}")
        print("\n📊 Preview of metrics & duration:")
        # Print a preview to verify our new features
        print(clean_df[['title', 'views', 'duration_sec', 'is_short']].head(3))
        print("\n")

        save_processed_data(clean_df, output_path)

    except FileNotFoundError:
        print(f"❌ Error: Could not find {input_path}.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")