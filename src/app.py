import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# Set the page configuration
st.set_page_config(page_title="BlindCreators | Dashboard", page_icon="👁️", layout="wide")


@st.cache_data
def load_data():
    """Connects to SQLite and loads the videos table."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "..", "data", "database.sqlite")
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM videos", conn)
        conn.close()
        return df
    except sqlite3.OperationalError:
        st.error(f"❌ Could not find database at {db_path}.")
        return pd.DataFrame()


# --- UI ---
st.title("👁️ BlindCreators Analytics")
st.markdown("Stop flying blind. Discover the data behind your content strategy.")

df = load_data()

if not df.empty:
    st.divider()  # Creates a visual horizontal line

    # --- 1. KPI SECTION ---
    st.subheader("📈 Channel Overview")
    # Create 4 columns for our top metrics
    col1, col2, col3, col4 = st.columns(4)

    total_views = df['views'].sum()
    total_likes = df['likes'].sum()
    total_videos = len(df)
    # Calculate average duration in minutes
    avg_duration_min = df['duration_sec'].mean() / 60

    # st.metric creates beautiful UI cards automatically
    col1.metric("Total Videos", f"{total_videos}")
    col2.metric("Total Views", f"{total_views:,}")  # The :, adds thousand separators
    col3.metric("Total Likes", f"{total_likes:,}")
    col4.metric("Avg Duration (min)", f"{avg_duration_min:.1f}")

    st.divider()

    # --- 2. CHARTS SECTION ---
    st.subheader("🎯 Performance Insights")
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("**Total Views by Day of the Week**")
        # Group data by day and sum the views
        day_stats = df.groupby('publish_day_name')['views'].sum().reset_index()
        # Sort to show the best day first
        day_stats = day_stats.sort_values(by='views', ascending=False)

        # Create an interactive bar chart with Plotly
        fig_day = px.bar(day_stats, x='publish_day_name', y='views',
                         color='views', color_continuous_scale='Viridis',
                         labels={'publish_day_name': 'Day of Week', 'views': 'Total Views'})
        st.plotly_chart(fig_day, use_container_width=True)

    with chart_col2:
        st.markdown("**Views: Shorts vs Regular Videos**")
        # Group by the 'is_short' boolean
        format_stats = df.groupby('is_short')['views'].sum().reset_index()
        # Rename True/False for the chart
        format_stats['Format'] = format_stats['is_short'].apply(lambda x: "Shorts" if x == 1 else "Regular Video")

        # Create a Donut chart
        fig_format = px.pie(format_stats, values='views', names='Format', hole=0.4,
                            color_discrete_sequence=['#FF4B4B', '#1f77b4'])
        st.plotly_chart(fig_format, use_container_width=True)

    st.divider()

    # --- 3. RAW DATA (Collapsed by default) ---
    # Using an expander keeps the UI clean but allows users to see the raw table if they want
    with st.expander("🔍 View Raw Database"):
        st.dataframe(df, use_container_width=True)