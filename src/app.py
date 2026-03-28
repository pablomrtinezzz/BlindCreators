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

# 1. PAGE CONFIGURATION (Must be the first command)
st.set_page_config(page_title="BlindCreators | Pro", page_icon="👁️", layout="wide", initial_sidebar_state="expanded")

# 2. INJECT CUSTOM CSS FOR MODERN TYPOGRAPHY AND STYLING
# We import 'Poppins' from Google Fonts and override Streamlit's default font
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Poppins', sans-serif;
    }

    /* Make metrics look like modern SaaS cards */
    div[data-testid="metric-container"] {
        background-color: #1e1e2f;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        border-left: 5px solid #8b5cf6; /* Neon Purple accent */
    }

    /* Style the tabs to look more like buttons */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1e1e2f;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        color: #a1a1aa;
    }
    .stTabs [aria-selected="true"] {
        background-color: #8b5cf6;
        color: white;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 3. GLOBAL PLOTLY THEME
import plotly.io as pio

pio.templates.default = "plotly_dark"
# A vibrant consumer-friendly color sequence (Purple, Electric Blue, Pink, Emerald)
BRAND_COLORS = ['#8b5cf6', '#3b82f6', '#ec4899', '#10b981']


@st.cache_data
def load_data():
    """Fetches all necessary metrics from the SQLite database."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "..", "data", "database.sqlite")
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM videos", conn)
        conn.close()

        if 'publish_time' in df.columns:
            df['publish_hour'] = df['publish_time'].str.split(':').str[0].astype(int)

        # Feature Engineering: Safe Engagement Rate calculation
        df['views_safe'] = df['views'].replace(0, 1)
        df['engagement_rate'] = (df['likes'] / df['views_safe']) * 100
        df = df.drop(columns=['views_safe'])

        return df
    except sqlite3.OperationalError:
        return pd.DataFrame()


# --- LOAD AND FILTER DATA ---
df = load_data()

if df.empty:
    st.error("❌ Database not found. Please run the ETL pipeline first.")
    st.stop()

# Interactive Sidebar Filters
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3137/3137852.png", width=50)  # Placeholder logo
    st.title("BlindCreators")
    st.markdown("---")
    video_type = st.radio("🎬 Content Format:", ["All Content", "Shorts Only", "Long Form Only"])

    if video_type == "Shorts Only":
        df = df[df['is_short'] == True]
    elif video_type == "Long Form Only":
        df = df[df['is_short'] == False]

    st.markdown("---")
    st.caption("v2.0 - Premium Edition")

# Filter outliers for clean visualizations (95th percentile)
threshold = df['views'].quantile(0.95)
df_filtered = df[df['views'] <= threshold]

# --- MAIN DASHBOARD HEADER ---
st.title("🚀 Channel Performance HQ")
st.markdown("Actionable insights, gorgeous visuals, and AI-driven strategy.")

# --- TOP METRICS (KPIs) ---
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Views", f"{df['views'].sum():,.0f}")
kpi2.metric("Likes", f"{df['likes'].sum():,.0f}")
kpi3.metric("Comments", f"{df['comments'].sum():,.0f}")
kpi4.metric("Avg. Engagement", f"{df['engagement_rate'].mean():.2f}%")
kpi5.metric("Total Videos", f"{len(df)}")

st.markdown("<br>", unsafe_allow_html=True)

# --- NAVIGATION TABS ---
tab_hall, tab_time, tab_seo, tab_ai = st.tabs([
    "🏆 Hall of Fame",
    "🕒 Timing & Heatmaps",
    "📈 SEO & Content",
    "🤖 AI Strategist"
])

# ==========================================
# TAB 1: HALL OF FAME (Top Videos with Thumbnails)
# ==========================================
with tab_hall:
    st.subheader("Your Top 5 All-Time Performers")
    st.markdown("The content that built your channel.")

    top_5 = df.sort_values(by='views', ascending=False).head(5)

    # Iterate through the top 5 videos and build a beautiful UI card for each
    for index, row in top_5.iterrows():
        with st.container(border=True):
            img_col, info_col, stats_col = st.columns([1, 3, 2])

            with img_col:
                # Display the actual YouTube thumbnail
                if 'thumbnail_url' in row and pd.notna(row['thumbnail_url']):
                    st.image(row['thumbnail_url'], use_container_width=True)
                else:
                    st.info("No thumbnail")

            with info_col:
                st.markdown(f"### {row['title']}")
                duration_str = f"{int(row['duration_sec'] // 60)}m {int(row['duration_sec'] % 60)}s"
                st.caption(f"📅 Published: {row.get('publish_day_name', 'Unknown')} | ⏱️ Duration: {duration_str}")

            with stats_col:
                st.markdown(f"**👁️ Views:** {row['views']:,.0f}")
                st.markdown(f"**👍 Likes:** {row['likes']:,.0f}")
                st.markdown(f"**🔥 Engagement:** {row['engagement_rate']:.2f}%")

# ==========================================
# TAB 2: TIMING & HEATMAPS
# ==========================================
with tab_time:
    col_time1, col_time2 = st.columns(2, gap="large")
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    with col_time1:
        st.markdown("**Upload Time Heatmap (Median Views)**")
        if 'publish_hour' in df_filtered.columns:
            heatmap_data = df_filtered.groupby(['publish_day_name', 'publish_hour'])['views'].median().reset_index()
            heatmap_pivot = heatmap_data.pivot(index='publish_day_name', columns='publish_hour', values='views').fillna(
                0)
            heatmap_pivot = heatmap_pivot.reindex(days_order)

            # Using a custom vivid color scale: Dark -> Blue -> Purple -> Pink
            custom_colorscale = ['#0f172a', '#3b82f6', '#8b5cf6', '#ec4899']

            fig_heat = px.imshow(
                heatmap_pivot,
                labels=dict(x="Hour of Day (UTC)", y="", color="Views"),
                x=[f"{h:02d}:00" for h in heatmap_pivot.columns],
                y=heatmap_pivot.index,
                color_continuous_scale=custom_colorscale,
                aspect="auto"
            )
            # Make the background transparent to blend with Streamlit
            fig_heat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_heat, use_container_width=True)

    with col_time2:
        st.markdown("**Performance by Day of the Week**")
        day_stats = df_filtered.groupby('publish_day_name')['views'].median().reset_index()
        day_stats['publish_day_name'] = pd.Categorical(day_stats['publish_day_name'], categories=days_order,
                                                       ordered=True)
        day_stats = day_stats.sort_values('publish_day_name')

        fig_day = px.bar(
            day_stats, x='publish_day_name', y='views',
            color='views', color_continuous_scale='Purples'
        )
        fig_day.update_layout(xaxis_title="", yaxis_title="Median Views", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_day, use_container_width=True)

# ==========================================
# TAB 3: SEO & CONTENT
# ==========================================
with tab_seo:
    col_seo1, col_seo2 = st.columns(2, gap="large")

    with col_seo1:
        st.markdown("**Top 15 Tags by Views**")
        tags_df = df_filtered.dropna(subset=['tags']).copy()
        tags_df['tags'] = tags_df['tags'].astype(str).str.split(',')
        tags_exploded = tags_df.explode('tags')
        tags_exploded['tags'] = tags_exploded['tags'].str.strip()
        tags_exploded = tags_exploded[tags_exploded['tags'] != '']

        tag_stats = tags_exploded.groupby('tags')['views'].median().reset_index()
        tag_stats = tag_stats.sort_values(by='views', ascending=True).tail(15)

        fig_tags = px.bar(
            tag_stats, x='views', y='tags', orientation='h',
            color='views', color_continuous_scale='Blues'
        )
        fig_tags.update_layout(yaxis_title="", xaxis_title="Median Views", paper_bgcolor="rgba(0,0,0,0)",
                               plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_tags, use_container_width=True)

    with col_seo2:
        st.markdown("**Retention vs. Reward (Scatter Plot)**")
        # Added scatter plot back! Shows Duration vs Views, bubble size is Likes
        fig_scatter = px.scatter(
            df_filtered, x='duration_sec', y='views',
            size='likes', color='engagement_rate',
            hover_name='title',
            color_continuous_scale='Sunset',
            size_max=30
        )
        fig_scatter.update_layout(xaxis_title="Duration (Seconds)", yaxis_title="Views", paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, use_container_width=True)

# ==========================================
# TAB 4: THE AI WAR ROOM (Strategist & Miner)
# ==========================================
with tab_ai:
    st.markdown("### 🤖 The AI War Room")
    st.caption(
        "Leverage Gemini to analyze your channel's historical DNA and extract ideas directly from your audience's comments.")

    # Create two sub-tabs inside the AI section for our two killer features
    ai_tab1, ai_tab2 = st.tabs(["💡 Concept Generator", "⛏️ Audience Miner"])

    with ai_tab1:
        with st.container(border=True):
            ai_col1, ai_col2 = st.columns([1, 1], gap="large")

            with ai_col1:
                user_topic = st.text_area("💡 Video Topic / Core Idea",
                                          placeholder="e.g., A deep dive into Elden Ring's hardest boss...", height=100)
                user_style = st.text_input("🎨 Vibe / Instructions (Optional)",
                                           placeholder="e.g., Make it mysterious, no clickbait.")
                generate_btn = st.button("✨ Generate Optimized Titles", type="primary", use_container_width=True)

            with ai_col2:
                if generate_btn:
                    if user_topic:
                        with st.spinner("Analyzing channel data & consulting Google Gemini..."):
                            hist_context = get_top_performing_titles()
                            ai_suggestions = generate_seo_titles(user_topic, hist_context, user_style)
                            st.success("Data-driven title ideas:")
                            st.info(ai_suggestions)
                    else:
                        st.warning("⚠️ Please provide a video topic to begin.")
                else:
                    st.info("Your AI-generated titles will appear here. Fill out the form and hit generate!")

    with ai_tab2:
        st.markdown("**Listen to the Data**")
        st.markdown(
            "We've extracted hundreds of real comments from your top videos. Click the button to let the AI find what your audience wants to watch next.")

        # A massive, full-width button to run the heavy analysis
        mine_btn = st.button("🔍 Run Audience Sentiment Analysis", type="primary", use_container_width=True)

        if mine_btn:
            with st.spinner("Processing natural language and clustering audience requests..."):
                # Dynamically import the new miner function
                try:
                    from ai_assistant import mine_audience_insights
                except ModuleNotFoundError:
                    from src.ai_assistant import mine_audience_insights

                mining_results = mine_audience_insights()

                st.success("Analysis Complete!")
                # Render the Markdown response safely inside a clean container
                with st.container(border=True):
                    st.markdown(mining_results)