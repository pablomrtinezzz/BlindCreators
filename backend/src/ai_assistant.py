import os
import sqlite3
import pandas as pd
from google import genai
from dotenv import load_dotenv
import json

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

def mine_audience_insights(json_path=None):
    """
    Reads the extracted YouTube comments and uses Gemini to analyze the audience's
    core desires, recurring themes, and suggests new video ideas.
    """
    try:
        # Resolve absolute path robustly regardless of where the script is run from
        if json_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "..", "data", "raw", "audience_comments.json")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data:
            return "No audience data found."

        # Aggregate all comments into a single text block to feed the LLM
        all_comments = []
        for video in data:
            all_comments.extend(video.get("comments", []))

        # Combine the comments into a bulleted list for the prompt
        combined_comments = "\n- ".join(all_comments)

        prompt = f"""
        You are a brilliant YouTube Content Strategist and Data Analyst.
        Below is a raw dump of recent comments from a creator's audience.

        Raw Audience Comments:
        - {combined_comments}

        Task:
        1. Analyze the sentiments, recurring lore debates, and weapon discussions in these comments.
        2. Identify 3 core topics or specific ideas that the audience is highly engaged with.
        3. Pitch 3 concrete, highly-clickable video concepts based exclusively on this data.

        Format your response clearly using Markdown, with engaging headings.
        Keep it strictly professional and actionable for a B2B SaaS platform.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text

    except FileNotFoundError:
        return f"❌ Audience comments file not found at path: {json_path}. Please run the extraction script first."
    except Exception as e:
        return f"❌ Error analyzing audience data: {e}"

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