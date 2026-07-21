import streamlit as st


def render_external_tool_links():
    """Keep the independently hosted tools visible beside Streamlit pages."""
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] hr,
        [data-testid="stSidebarNavSeparator"] {
            display: none !important;
        }
        [data-testid="stSidebarUserContent"] {
            padding-top: 0 !important;
            margin-top: -12px !important;
        }
        [data-testid="stSidebar"] div[data-testid="stPageLink"] {
            width: 100%;
        }
        [data-testid="stSidebar"] div[data-testid="stPageLink"] a {
            width: 100% !important;
            height: 28px !important;
            min-height: 28px !important;
            box-sizing: border-box !important;
            padding: 0 8px !important;
            border: 0 !important;
            border-radius: 6px !important;
            justify-content: flex-start !important;
            color: inherit !important;
            background: transparent !important;
            box-shadow: none !important;
            text-decoration: none !important;
        }
        [data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover {
            color: inherit !important;
            background: rgba(151, 166, 195, 0.15) !important;
        }
        [data-testid="stSidebar"] div[data-testid="stPageLink"] p {
            font-size: 1rem !important;
            font-weight: 400 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.page_link(
        "https://lily666-lab.github.io/AuditMind/",
        label="AuditMind",
        icon="🧾",
    )
    st.sidebar.page_link(
        "https://wangcai-todo.basic-coati-8835.chatgpt.site",
        label="Wangcai Todo",
        icon="🐕",
    )
    st.sidebar.page_link(
        "https://lily666-lab.github.io/miaowu-note/",
        label="Miaowu Note",
        icon="🐱",
    )
