import json
import pandas as pd
import os


def load_raw_data(filepath):
    """Loads raw JSON data from the specified path."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def transform_video_data(raw_data):
    """
    Cleans and transforms raw video dictionaries into a pandas DataFrame.
    Performs Feature Engineering and drops redundant columns.
    """
    # 1. Convert list of dictionaries to a Pandas DataFrame
    df = pd.DataFrame(raw_data)

    # 2. Convert 'published_at' string to actual datetime objects
    df['published_at'] = pd.to_datetime(df['published_at'])

    # 3. Feature Engineering: Extract Day and exact Time
    df['publish_day_name'] = df['published_at'].dt.day_name()
    # strftime converts the datetime object into a formatted string (HH:MM)
    df['publish_time'] = df['published_at'].dt.strftime('%H:%M')

    # 4. Drop the original and now redundant 'published_at' column
    df = df.drop(columns=['published_at'])

    return df


def save_processed_data(df, filepath):
    """Saves the cleaned DataFrame to a CSV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    # index=False prevents pandas from saving row numbers
    df.to_csv(filepath, index=False, encoding='utf-8')
    print(f"📁 Processed data saved successfully to {filepath}")


if __name__ == "__main__":
    input_path = ("../data/raw/eldentips_raw_videos.json")
    output_path = "../data/processed/eldentips_cleaned_videos.csv"

    print("🔄 Starting data transformation...")

    try:
        # Load
        raw_videos = load_raw_data(input_path)

        # Transform
        clean_df = transform_video_data(raw_videos)

        # Quick preview in console
        print(f"✅ Data transformed. Total videos: {clean_df.shape[0]}")
        print("\nPreview of the cleaned data:")
        # Print the first 3 rows, but only specific columns to keep it clean
        print(clean_df[['title', 'publish_day_name', 'publish_time']].head(3))
        print("\n")

        # Save
        save_processed_data(clean_df, output_path)

    except FileNotFoundError:
        print(f"❌ Error: Could not find {input_path}. Did you run extract.py first?")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")