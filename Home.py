import base64
from pathlib import Path

import streamlit as st

from sidebar import render_external_tool_links


st.set_page_config(
    page_title="Lily’s Insight Hub",
    page_icon="✨",
    layout="wide",
)

render_external_tool_links()


def image_data_uri(filename):
    image_path = Path(__file__).with_name(filename)
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


banner_uri = image_data_uri("banner.jpg")

st.markdown(
    """
    <style>
    .stApp {
        background-color: #ffffff;
    }
    .block-container {
        max-width: 1280px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    .hero-banner {
        min-height: 230px;
        margin-bottom: 1.35rem;
        padding: 2.25rem 2rem;
        border-radius: 14px;
        background-position: center;
        background-size: cover;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        box-shadow: 0 12px 28px rgba(33, 31, 42, 0.12);
    }
    .hero-title {
        color: #ffffff;
        font-size: clamp(2rem, 4vw, 3.25rem);
        font-weight: 800;
        line-height: 1.15;
        letter-spacing: 0.2px;
        text-shadow: 0 3px 16px rgba(18, 17, 28, 0.52);
    }
    .hero-subtitle {
        max-width: 780px;
        margin-top: 0.8rem;
        color: rgba(255, 255, 255, 0.96);
        font-size: 1.05rem;
        font-weight: 500;
        line-height: 1.6;
        text-shadow: 0 2px 10px rgba(18, 17, 28, 0.58);
    }
    .tool-icon {
        height: 64px;
        display: flex;
        align-items: center;
        font-size: 2.7rem;
        line-height: 1;
    }
    .card-title {
        min-height: 3.35rem;
        margin-top: 0.35rem;
        margin-bottom: 0.35rem;
        color: #111111;
        font-size: 1.35rem;
        font-weight: 750;
        line-height: 1.35;
    }
    .card-subtitle {
        min-height: 3.7rem;
        margin-bottom: 0.8rem;
        color: #4a4a4a;
        font-size: 1.01rem;
        line-height: 1.55;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #dedede;
        border-radius: 14px;
        background: #ffffff;
        box-shadow: 0 4px 14px rgba(20, 20, 20, 0.035);
    }
    div[data-testid="stPageLink"] {
        width: 100%;
    }
    div[data-testid="stPageLink"] a {
        width: 100%;
        height: 2.5rem;
        min-height: 2.5rem;
        box-sizing: border-box;
        padding: 0.375rem 0.75rem;
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 0.6rem;
        justify-content: center;
        color: #31333f;
        background: #ffffff;
        text-decoration: none;
        transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
    }
    div[data-testid="stPageLink"] a:hover {
        border-color: #ff4b4b;
        color: #ff4b4b;
        background: #fffafa;
    }
    div[data-testid="stColumn"] div[data-testid="stVerticalBlock"]
    > div[data-testid="stElementContainer"]:last-child {
        margin-top: auto;
    }
    @media (max-width: 700px) {
        .block-container {
            padding-top: 0.7rem;
        }
        .hero-banner {
            min-height: 200px;
            padding: 1.8rem 1.1rem;
        }
        .hero-subtitle {
            font-size: 0.95rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <section class="hero-banner" style="background-image:
        linear-gradient(90deg, rgba(20, 15, 35, 0.35), rgba(20, 15, 35, 0.18)),
        url('{banner_uri}');">
        <div class="hero-title">✨ Welcome To Lily’s Insight Hub</div>
        <div class="hero-subtitle">A collection of AI-powered research and productivity tools built by Lily.</div>
    </section>
    """,
    unsafe_allow_html=True,
)


def render_tool_card(
    column,
    title,
    subtitle,
    button_label,
    *,
    image=None,
    image_width=60,
    emoji=None,
    page=None,
    url=None,
):
    with column:
        with st.container(border=True, height=330):
            if image:
                st.image(image, width=image_width)
            else:
                st.markdown(
                    f'<div class="tool-icon">{emoji}</div>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<div class="card-title">{title}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="card-subtitle">{subtitle}</div>',
                unsafe_allow_html=True,
            )

            if page:
                st.page_link(page, label=button_label, width="stretch")
            else:
                st.link_button(button_label, url, width="stretch")


first_row = st.columns(3, gap="large")

render_tool_card(
    first_row[0],
    "YouTube 数据分析",
    "深度剖析爆款视频数据与内容结构",
    "进入 YouTube 分析",
    image="youtube_logo.png",
    page="pages/1_📺_YouTube_Analyzer.py",
)

render_tool_card(
    first_row[1],
    "Reddit 数据分析",
    "一键获取海外学习者的真实痛点与讨论",
    "进入 Reddit 分析",
    image="reddit_logo.png",
    page="pages/2_🍎_Reddit_Data_Scraper.py",
)

render_tool_card(
    first_row[2],
    "AuditMind",
    "你的AI审计工作伙伴",
    "进入 AuditMind",
    image="auditmind_card.png",
    image_width=120,
    url="https://lily666-lab.github.io/AuditMind/",
)

st.markdown('<div style="height: 0.15rem"></div>', unsafe_allow_html=True)
second_row = st.columns(3, gap="large")

render_tool_card(
    second_row[0],
    "旺财 Todo",
    "把任务投喂给旺财，轻松管理每一天",
    "进入旺财 Todo",
    emoji="🐕",
    url="https://wangcai-todo.basic-coati-8835.chatgpt.site",
)

render_tool_card(
    second_row[1],
    "喵呜笔记",
    "随手记录灵感，用分类和标签整理想法",
    "进入喵呜笔记",
    emoji="🐱",
    url="https://lily666-lab.github.io/miaowu-note/",
)
