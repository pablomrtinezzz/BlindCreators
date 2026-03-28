import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# IMPORT OUR AI MODULE
try:
    from ai_assistant import get_top_performing_titles, generate_seo_titles
except ModuleNotFoundError:
    from src.ai_assistant import get_top_performing_titles, generate_seo_titles

@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "..", "data", "database.sqlite")
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM videos", conn)
        conn.close()

        if 'publish_time' in df.columns:
            df['publish_hour'] = df['publish_time'].str.split(':').str[0].astype(int)

        # Feature Engineering: Engagement Rate (Likes per 100 views)
        # We avoid division by zero by replacing 0 views with 1 temporarily
        df['views_safe'] = df['views'].replace(0, 1)
        df['engagement_rate'] = (df['likes'] / df['views_safe']) * 100
        df = df.drop(columns=['views_safe'])

        return df
    except sqlite3.OperationalError:
        st.error(f"❌ Could not find database at {db_path}.")
        return pd.DataFrame()


# --- UI ---
st.title("👁️ BlindCreators Analytics")
st.markdown("Stop flying blind. Discover the true data behind your content strategy.")

df = load_data()

if not df.empty:
    st.divider()

    # --- 1. KPI SECTION (All Data) ---
    st.subheader("📈 Channel Overview")
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Videos", f"{len(df)}")
    col2.metric("Total Views", f"{df['views'].sum():,}")
    avg_engagement = df['engagement_rate'].mean()
    col3.metric("Avg. Engagement Rate", f"{avg_engagement:.2f}%")
    col4.metric("Avg Duration (min)", f"{(df['duration_sec'].mean() / 60):.1f}")

    st.divider()

    # --- FILTERING OUTLIERS FOR CHARTS ---
    threshold = df['views'].quantile(0.90)
    df_filtered = df[df['views'] <= threshold]

    # --- 2. TIMING ANALYSIS ---
    st.subheader("🕒 When to Publish? (Timing Analysis)")
    time_col1, time_col2 = st.columns(2)

    with time_col1:
        st.markdown("**Performance by Day of the Week**")
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_stats = df_filtered.groupby('publish_day_name')['views'].median().reset_index()
        day_stats['publish_day_name'] = pd.Categorical(day_stats['publish_day_name'], categories=days_order,
                                                       ordered=True)
        day_stats = day_stats.sort_values('publish_day_name')

        fig_day = px.bar(day_stats, x='publish_day_name', y='views',
                         color='views', color_continuous_scale='Blues',
                         labels={'publish_day_name': 'Day', 'views': 'Median Views'})
        st.plotly_chart(fig_day, use_container_width=True)

    with time_col2:
        st.markdown("**Top 10 Best Posting Hours**")
        if 'publish_hour' in df_filtered.columns:
            hour_stats = df_filtered.groupby('publish_hour')['views'].median().reset_index()
            hour_stats = hour_stats.sort_values(by='views', ascending=False).head(10)
            hour_stats['publish_hour'] = hour_stats['publish_hour'].astype(str) + ":00"

            fig_hour = px.bar(hour_stats, x='publish_hour', y='views',
                              color='views', color_continuous_scale='Purples',
                              labels={'publish_hour': 'Hour of Day (UTC)', 'views': 'Median Views'})
            st.plotly_chart(fig_hour, use_container_width=True)

    st.divider()

    # --- 3. CONTENT & SEO ANALYSIS ---
    st.subheader("💡 What to Publish? (Content & SEO)")
    content_col1, content_col2 = st.columns(2)

    with content_col1:
        st.markdown("**Top 15 Tags by Views**")
        tags_df = df_filtered.dropna(subset=['tags']).copy()
        tags_df['tags'] = tags_df['tags'].astype(str).str.split(',')
        tags_exploded = tags_df.explode('tags')
        tags_exploded['tags'] = tags_exploded['tags'].str.strip()
        tags_exploded = tags_exploded[tags_exploded['tags'] != '']

        tag_stats = tags_exploded.groupby('tags')['views'].median().reset_index()
        tag_stats = tag_stats.sort_values(by='views', ascending=True).tail(15)

        # FIXED: Changed 'Emerald' to 'emrld'
        fig_tags = px.bar(tag_stats, x='views', y='tags', orientation='h',
                          color='views', color_continuous_scale='emrld',
                          labels={'tags': 'Hashtag', 'views': 'Median Views'})
        st.plotly_chart(fig_tags, use_container_width=True)

    with content_col2:
        st.markdown("**Video Duration vs. Views (Scatter)**")
        # Added size parameter based on likes to make it more insightful
        fig_scatter = px.scatter(df_filtered, x='duration_sec', y='views',
                                 size='likes', hover_data=['title'],
                                 color='views', color_continuous_scale='Inferno',
                                 labels={'duration_sec': 'Duration (Seconds)', 'views': 'Views'})
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()

    # --- 4. ENGAGEMENT ANALYSIS ---
    st.subheader("🔥 Audience Engagement")
    eng_col1, eng_col2 = st.columns(2)

    with eng_col1:
        st.markdown("**Top 5 Videos by Engagement Rate (%)**")
        # Shows which videos actually made people click "like" relative to their views
        top_engaged = df[df['views'] > 100].sort_values(by='engagement_rate', ascending=False).head(5)
        fig_eng = px.bar(top_engaged, x='engagement_rate', y='title', orientation='h',
                         color='engagement_rate', color_continuous_scale='solar',
                         labels={'title': 'Video Title', 'engagement_rate': 'Engagement Rate (%)'})
        # Hide the y-axis labels if they are too long
        fig_eng.update_yaxes(showticklabels=False)
        st.plotly_chart(fig_eng, use_container_width=True)

    st.divider()

    with st.expander("🔍 View Raw Database"):
        st.dataframe(df.drop(columns=['publish_hour'], errors='ignore'), use_container_width=True)

    # --- 5. AI SEO TITLE GENERATOR ---
    st.subheader("🤖 AI Content Strategist")
    st.markdown(
        "Let Gemini analyze your channel's historical data to suggest highly clickable titles for your next video.")

    # Create a visually distinct container for the AI tool
    with st.container(border=True):
        ai_col1, ai_col2 = st.columns([2, 1])

        with ai_col1:
            user_topic = st.text_input("💡 What is your next video about?",
                                       placeholder="e.g., How to beat Malenia with magic...")

        with ai_col2:
            user_style = st.text_input("🎨 Any specific vibe? (Optional)",
                                       placeholder="e.g., Make it mysterious, use emojis...")

        # The button that triggers the LLM
        if st.button("✨ Generate Viral Titles", type="primary", use_container_width=True):
            if user_topic:
                with st.spinner("Analyzing your channel's DNA and consulting Google Gemini..."):
                    # 1. Retrieve the context (RAG pattern)
                    hist_context = get_top_performing_titles()

                    # 2. Call Gemini API
                    ai_suggestions = generate_seo_titles(user_topic, hist_context, user_style)

                    # 3. Display the result
                    st.success("Here are your data-driven title ideas:")
                    st.info(ai_suggestions)
            else:
                st.warning("⚠️ Please enter a video topic first.")