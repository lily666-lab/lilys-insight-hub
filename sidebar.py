import streamlit as st


def render_external_tool_links():
    """Keep the independently hosted tools visible beside Streamlit pages."""
    st.sidebar.divider()
    st.sidebar.caption("MORE AI TOOLS")
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
