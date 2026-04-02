import streamlit as st

st.set_page_config(
    page_title="Lily’s Insight Hub",
    page_icon="✨",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #ffffff;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }
    .hero-title {
        text-align: center;
        font-size: 3.2rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin-top: 0.8rem;
        margin-bottom: 2rem;
        color: #111111;
    }
    .card-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 0.4rem;
        margin-bottom: 0.4rem;
        color: #111111;
    }
    .card-subtitle {
        font-size: 1.02rem;
        color: #444444;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.image("banner.jpg")

st.markdown(
    '<div class="hero-title">✨ Welcome To Lily’s Insight Hub</div>',
    unsafe_allow_html=True,
)

left_col, right_col = st.columns(2, gap="large")

with left_col:
    with st.container(border=True):
        st.image("youtube_logo.png", width=60)
        st.markdown('<div class="card-title">YouTube 数据分析</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">深度剖析爆款视频数据与内容结构</div>',
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/1_📺_YouTube_Analyzer.py",
            label="进入 YouTube 分析",
        )

with right_col:
    with st.container(border=True):
        st.image("reddit_logo.png", width=60)
        st.markdown('<div class="card-title">Reddit 数据分析</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">一键获取海外学习者的真实痛点与讨论</div>',
            unsafe_allow_html=True,
        )
        st.page_link(
            "pages/2_🍎_Reddit_Data_Scraper.py",
            label="进入 Reddit 分析",
        )