import os
import sqlite3
import pandas as pd
from google import genai
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file!")

# 2. Configure the new Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)


def get_top_performing_titles(db_path="../data/database.sqlite", limit=5):
    """
    Retrieves the titles of the top performing videos from the database
    to use as context for the AI (RAG pattern).
    """
    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT title, views FROM videos ORDER BY views DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return "No historical data available."

        context = "\n".join([f"- {row['title']} (Generated {row['views']} views)" for _, row in df.iterrows()])
        return context
    except Exception as e:
        print(f"Error reading database: {e}")
        return ""


def generate_seo_titles(video_topic, channel_context, extra_instructions=""):
    """
    Calls the Google Gemini API to generate SEO-optimized titles
    based on the user's historical success and optional styling constraints.
    """
    prompt = f"""
    You are an expert YouTube SEO strategist and copywriter.
    Your client is a content creator. 

    Here are their top-performing videos historically to help you understand their style, 
    niche, and what their audience clicks on:
    {channel_context}

    The creator wants to make a new video about the following topic:
    "{video_topic}"

    Task:
    Suggest 3 highly clickable, SEO-optimized YouTube titles for this new video.
    Match the style and format of their past successful videos.
    Keep them under 60 characters if possible to avoid truncation on mobile.
    """

    # Inject the extra string requested by the user
    if extra_instructions:
        prompt += f"\nCRITICAL INSTRUCTION FROM CREATOR: {extra_instructions}\n"

    prompt += "\nReturn ONLY the 3 titles in a numbered list. Do not include any other text."

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ Error connecting to Gemini: {e}"


if __name__ == "__main__":
    print("🧠 Initializing BlindCreators AI Assistant...\n")

    print("📊 Fetching historical context from database...")
    context = get_top_performing_titles()
    print("Top videos found:")
    print(f"{context}\n")

    test_topic = "How to defeat Malenia easily with a magic build"
    print(f"🎯 Generating titles for new video idea: '{test_topic}'...\n")

    result = generate_seo_titles(test_topic, context)

    print("✨ AI Suggestions:")
    print(result)