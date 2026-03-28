import streamlit as st
import pandas as pd
import sqlite3
import os

# Set the page configuration (Must be the first Streamlit command)
st.set_page_config(page_title="BlindCreators | Dashboard", page_icon="👁️", layout="wide")


@st.cache_data
def load_data():
    """
    Connects to the SQLite database and loads the videos table.
    Uses st.cache_data to speed up load times.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "..", "data", "database.sqlite")

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM videos", conn)
        conn.close()
        return df
    except sqlite3.OperationalError:
        st.error(f"❌ Could not find database at {db_path}. Please run the ETL pipeline first.")
        return pd.DataFrame()


# --- UI ---
st.title("👁️ BlindCreators Analytics Dashboard")
st.markdown("Discover the data behind your content and stop flying blind.")

# Load the data
df = load_data()

if not df.empty:
    st.success(f"Successfully loaded {len(df)} videos from the database.")

    st.subheader("Raw Data Preview")
    # Display the dataframe as an interactive table
    st.dataframe(df)