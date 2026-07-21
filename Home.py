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
    .hero-subtitle {
        max-width: 760px;
        margin: -1.2rem auto 2rem;
        text-align: center;
        color: #666666;
        font-size: 1.05rem;
        line-height: 1.7;
    }
    .tool-icon {
        height: 60px;
        display: flex;
        align-items: center;
        font-size: 2.7rem;
        line-height: 1;
    }
    .card-title {
        min-height: 3.1rem;
        font-size: 1.35rem;
        font-weight: 700;
        margin-top: 0.4rem;
        margin-bottom: 0.4rem;
        color: #111111;
        line-height: 1.35;
    }
    .card-subtitle {
        min-height: 3.4rem;
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

st.markdown(
    '<div class="hero-subtitle">A collection of AI-powered research and productivity tools built by Lily.</div>',
    unsafe_allow_html=True,
)

youtube_col, reddit_col, auditmind_col = st.columns(3, gap="large")

with youtube_col:
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

with reddit_col:
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

with auditmind_col:
    with st.container(border=True):
        st.image("auditmind_card.png", width=120)
        st.markdown('<div class="card-title">AuditMind</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">你的AI审计工作伙伴</div>',
            unsafe_allow_html=True,
        )
        st.link_button(
            "进入 AuditMind",
            "https://lily666-lab.github.io/AuditMind/",
            width="stretch",
        )

st.markdown("<br>", unsafe_allow_html=True)
_, wangcai_col, miaowu_col, _ = st.columns([0.45, 1, 1, 0.45], gap="large")

with wangcai_col:
    with st.container(border=True):
        st.markdown('<div class="tool-icon">🐕</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-title">旺财 Todo</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">把任务投喂给旺财，轻松管理每一天</div>',
            unsafe_allow_html=True,
        )
        st.link_button(
            "进入旺财 Todo",
            "https://wangcai-todo.basic-coati-8835.chatgpt.site",
            width="stretch",
        )

with miaowu_col:
    with st.container(border=True):
        st.markdown('<div class="tool-icon">🐱</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-title">喵呜笔记</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="card-subtitle">随手记录灵感，用分类和标签整理想法</div>',
            unsafe_allow_html=True,
        )
        st.link_button(
            "进入喵呜笔记",
            "https://lily666-lab.github.io/miaowu-note/",
            width="stretch",
        )
