import re
from datetime import datetime, time, timezone
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import isodate
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi

try:
    from youtube_transcript_api._errors import (
        CouldNotRetrieveTranscript,
        IpBlocked,
        NoTranscriptFound,
        RequestBlocked,
        TranscriptsDisabled,
        VideoUnavailable,
    )

    TRANSCRIPT_SKIP_EXCEPTIONS = (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        RequestBlocked,
        IpBlocked,
        CouldNotRetrieveTranscript,
    )
except Exception:
    TRANSCRIPT_SKIP_EXCEPTIONS = (Exception,)

st.set_page_config(page_title="YouTube 竞品分析工具", layout="wide")


def inject_global_css():
    st.markdown(
        """
        <style>
        :root {
            --yt-red: #FF0000;
            --bg: #FFFFFF;
            --text: #000000;
            --link-blue: #1a73e8;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        .stApp, .stMarkdown, p, div, label, span, h1, h2, h3, h4 {
            color: var(--text);
        }

        .stButton > button[kind="primary"] {
            background-color: var(--yt-red) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--yt-red) !important;
            border-radius: 10px !important;
        }

        .stButton > button[kind="primary"]:hover {
            background-color: #d90000 !important;
            border-color: #d90000 !important;
            color: #FFFFFF !important;
        }

        .stDownloadButton > button {
            background-color: var(--yt-red) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--yt-red) !important;
            border-radius: 10px !important;
        }

        .stDownloadButton > button:hover {
            background-color: #d90000 !important;
            border-color: #d90000 !important;
            color: #FFFFFF !important;
        }

        .stProgress > div > div > div > div {
            background-color: var(--yt-red) !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--yt-red) !important;
            font-weight: 800 !important;
        }

        .yt-banner {
            display: flex;
            align-items: center;
            gap: 12px;
            background: #FF0000;
            color: white;
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 12px;
        }

        .yt-play {
            width: 34px;
            height: 24px;
            background: white;
            border-radius: 6px;
            position: relative;
            flex-shrink: 0;
        }

        .yt-play:before {
            content: "";
            position: absolute;
            left: 12px;
            top: 6px;
            width: 0;
            height: 0;
            border-top: 6px solid transparent;
            border-bottom: 6px solid transparent;
            border-left: 10px solid #FF0000;
        }

        .subtitle-muted { color: #444444; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_banner():
    st.markdown(
        """
        <div class="yt-banner">
            <div class="yt-play"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:42px;font-weight:900;line-height:1.05;margin:4px 0 10px 0;'>YouTube 竞品分析工具</div>",
        unsafe_allow_html=True,
    )


def init_session_state():
    if "page_mode" not in st.session_state:
        st.session_state.page_mode = "home"
    if "selected_video_idx" not in st.session_state:
        st.session_state.selected_video_idx = None
    if "full_df" not in st.session_state:
        st.session_state.full_df = pd.DataFrame()
    if "list_df" not in st.session_state:
        st.session_state.list_df = pd.DataFrame()
    if "last_run_ok" not in st.session_state:
        st.session_state.last_run_ok = False


def build_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)


def extract_video_id(text: str):
    text = (text or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", text):
        return text

    try:
        parsed = urlparse(text)
        host = parsed.netloc.lower()
        path = parsed.path

        if "youtu.be" in host:
            vid = path.strip("/").split("/")[0]
            return vid if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or "") else None

        if "youtube.com" in host:
            if path == "/watch":
                v = parse_qs(parsed.query).get("v", [None])[0]
                return v if re.fullmatch(r"[A-Za-z0-9_-]{11}", v or "") else None

            m = re.search(r"/(shorts|embed)/([A-Za-z0-9_-]{11})", path)
            if m:
                return m.group(2)
    except Exception:
        return None

    return None


def resolve_channel_id(channel_input: str, youtube):
    raw = (channel_input or "").strip()

    if re.fullmatch(r"UC[a-zA-Z0-9_-]{22}", raw):
        return raw

    if raw.startswith("@"):
        cid = channel_id_by_handle(youtube, raw[1:])
        if cid:
            return cid

    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        path = parsed.path.strip("/")
        parts = path.split("/") if path else []

        if len(parts) >= 2 and parts[0] == "channel":
            cid = parts[1]
            if re.fullmatch(r"UC[a-zA-Z0-9_-]{22}", cid):
                return cid

        if len(parts) >= 1 and parts[0].startswith("@"):
            cid = channel_id_by_handle(youtube, parts[0][1:])
            if cid:
                return cid

        if len(parts) >= 2 and parts[0] == "user":
            username = parts[1]
            try:
                resp = youtube.channels().list(part="id", forUsername=username).execute()
                items = resp.get("items", [])
                if items:
                    return items[0]["id"]
            except Exception:
                pass

        keyword = parts[-1] if parts else raw
        cid = search_channel_id(youtube, keyword)
        if cid:
            return cid

    return search_channel_id(youtube, raw)


def channel_id_by_handle(youtube, handle: str):
    try:
        resp = youtube.channels().list(part="id", forHandle=handle).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]
    except Exception:
        pass

    cid = search_channel_id(youtube, f"@{handle}")
    if cid:
        return cid
    return search_channel_id(youtube, handle)


def search_channel_id(youtube, keyword: str):
    try:
        resp = youtube.search().list(
            part="snippet",
            q=keyword,
            type="channel",
            maxResults=5,
        ).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
    except Exception:
        pass
    return None


def get_latest_channel_video_ids(
    youtube,
    channel_id: str,
    max_results=50,
    published_after=None,
    published_before=None,
):
    params = {
        "part": "id,snippet",
        "channelId": channel_id,
        "order": "date",
        "type": "video",
        "maxResults": min(max_results, 50),
    }
    if published_after:
        params["publishedAfter"] = published_after
    if published_before:
        params["publishedBefore"] = published_before

    resp = youtube.search().list(**params).execute()
    items = resp.get("items", [])
    return [i.get("id", {}).get("videoId") for i in items if i.get("id", {}).get("videoId")]


def chunked(seq, size=50):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def fetch_videos_details(youtube, video_ids):
    all_items = []
    for ids in chunked(video_ids, 50):
        resp = youtube.videos().list(part="snippet,contentDetails,statistics", id=",".join(ids)).execute()
        all_items.extend(resp.get("items", []))
    return all_items


def choose_best_thumbnail(snippet):
    thumbs = snippet.get("thumbnails", {})
    for key in ["maxres", "standard", "high", "medium", "default"]:
        if key in thumbs and thumbs[key].get("url"):
            return thumbs[key]["url"]
    return ""


def safe_int(x):
    try:
        return int(x)
    except Exception:
        return 0


def view_level(view_count: int):
    if view_count < 5000:
        return "5000以下"
    if view_count < 10000:
        return "5000-1万"
    return "1万以上"


def calc_engagement_rate(like_count: int, view_count: int):
    if view_count <= 0:
        return 0.0
    return round((like_count / view_count) * 100, 2)


def fetch_transcript_text(video_id: str):
    v = str(video_id or "").strip()
    if "youtube.com" in v or "youtu.be" in v or v.startswith("http"):
        extracted = extract_video_id(v)
        if extracted:
            v = extracted

    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", v):
        return "为保护当前节点，已自动跳过字幕"

    try:
        transcript = YouTubeTranscriptApi().fetch(
            v,
            languages=[
                "en",
                "en-US",
                "en-GB",
                "zh-Hans",
                "zh-CN",
                "zh",
                "zh-TW",
                "zh-Hant",
                "ja",
                "ko",
                "es",
                "fr",
                "de",
                "ru",
            ],
        )
        parts = []
        for item in transcript:
            if isinstance(item, dict):
                t = item.get("text", "")
            else:
                t = getattr(item, "text", "")
            if t:
                parts.append(t)
        text = " ".join(parts).strip()
        return text if text else "为保护当前节点，已自动跳过字幕"
    except TRANSCRIPT_SKIP_EXCEPTIONS:
        return "为保护当前节点，已自动跳过字幕"
    except Exception:
        return "为保护当前节点，已自动跳过字幕"


def human_http_error(e: HttpError):
    status = getattr(e.resp, "status", None)
    msg = str(e)
    if status in (400, 403):
        if "API key not valid" in msg or "keyInvalid" in msg:
            return "API Key 无效，请检查后重试。"
        if "quotaExceeded" in msg:
            return "YouTube API 配额已耗尽，请稍后再试或更换 Key。"
        return "请求被拒绝（可能是参数错误、权限不足或配额限制）。"
    if status == 404:
        return "资源不存在，请检查视频或频道链接是否正确。"
    return f"调用 YouTube API 失败（HTTP {status}）。请稍后重试。"


def build_full_dataframe(video_items, selected_fields_keys):
    rows = []
    total = len(video_items)
    progress = st.progress(0, text="开始处理视频...")

    want_transcript = "transcript" in selected_fields_keys

    for idx, item in enumerate(video_items, start=1):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})

        video_id = item.get("id", "")
        title = snippet.get("title", "")
        desc = snippet.get("description", "")
        tags = ", ".join(snippet.get("tags", [])) if snippet.get("tags") else ""
        thumbnail = choose_best_thumbnail(snippet)

        views = safe_int(stats.get("viewCount", 0))
        likes = safe_int(stats.get("likeCount", 0))
        level = view_level(views)
        engagement = calc_engagement_rate(likes, views)
        published_at = snippet.get("publishedAt", "")

        try:
            published_date = pd.to_datetime(published_at).date().isoformat() if published_at else ""
        except Exception:
            published_date = ""

        transcript_text = fetch_transcript_text(video_id) if want_transcript else ""

        rows.append(
            {
                "视频ID": video_id,
                "视频链接": f"https://www.youtube.com/watch?v={video_id}",
                "发布日期": published_date,
                "发布时间": published_at,
                "标题": title,
                "描述": desc,
                "标签": tags,
                "封面图": thumbnail,
                "播放量": views,
                "点赞量": likes,
                "播放量级别": level,
                "互动率 (%)": engagement,
                "ISO时长": content.get("duration", ""),
                "视频字幕文案": transcript_text,
            }
        )

        progress.progress(idx / max(total, 1), text=f"处理中：{idx}/{total}")

    progress.empty()
    return pd.DataFrame(rows)


def build_list_df(full_df, selected_levels, selected_fields_keys):
    if full_df.empty:
        return full_df

    df = full_df.copy()
    if selected_levels:
        df = df[df["播放量级别"].isin(selected_levels)].copy()
    else:
        df = df.iloc[0:0].copy()

    df = df.reset_index().rename(columns={"index": "__row_idx__"})
    return df


def to_excel_bytes(df: pd.DataFrame):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="YouTube分析结果")
    bio.seek(0)
    return bio.getvalue()


FIELD_DEFS = [
    ("publish_date", "发布日期", "Publish Date", True),
    ("title", "标题", "Title", True),
    ("description", "描述", "Description", True),
    ("tags", "标签", "Tags", True),
    ("thumbnail", "封面图", "Thumbnail", True),
    ("view_count", "播放量", "View Count", True),
    ("like_count", "点赞量", "Like Count", True),
    ("transcript", "字幕", "Transcript", True),
    ("view_level", "播放量级别", "View Level", True),
]


def render_sidebar():
    st.sidebar.markdown("### 配置区")
    api_key = st.sidebar.text_input("YouTube API Key", type="password")

    with st.sidebar.expander("🔑 基础配置", expanded=True):
        mode = st.radio(
            "输入模式",
            ["模式 A：分析单个视频", "模式 B：分析频道（最多50个最新视频）"],
            key="mode",
        )
        video_type_filter = "全部"
        if mode.startswith("模式 B"):
            video_type_filter = st.selectbox(
                "视频类型筛选（仅模式 B）",
                ["全部", "仅长视频（>=60秒）", "仅 Shorts（<60秒）"],
            )

    with st.sidebar.expander("📅 时间筛选", expanded=False):
        enable_date_filter = st.checkbox("启用发布时间筛选", value=False)
        selected_date_range = ()
        if enable_date_filter:
            selected_date_range = st.date_input("选择起始和结束日期", value=())

    with st.sidebar.expander("🎯 选择字段与展示", expanded=False):
        st.caption("勾选后将影响抓取内容（如字幕）与展示。")
        selected_fields_keys = []
        for k, cn, en, default_on in FIELD_DEFS:
            if st.checkbox(f"{cn} ({en})", value=default_on, key=f"field_{k}"):
                selected_fields_keys.append(k)

    selected_levels = st.sidebar.multiselect(
        "播放量级别筛选（多选）",
        options=["5000以下", "5000-1万", "1万以上"],
        default=["5000以下", "5000-1万", "1万以上"],
    )

    return {
        "api_key": api_key,
        "mode": mode,
        "video_type_filter": video_type_filter,
        "enable_date_filter": enable_date_filter,
        "selected_date_range": selected_date_range,
        "selected_levels": selected_levels,
        "selected_fields_keys": selected_fields_keys,
    }


def run_analysis(config, user_input):
    if not config["api_key"].strip():
        st.error("请先在左侧填写 YouTube API Key。")
        return

    if not user_input.strip():
        st.error("请输入有效的视频链接 / 视频ID / 频道链接 / Channel ID。")
        return

    try:
        youtube = build_youtube_client(config["api_key"].strip())

        with st.spinner("正在请求 YouTube 数据，请稍候..."):
            if config["mode"].startswith("模式 A"):
                vid = extract_video_id(user_input)
                if not vid:
                    st.error("视频链接或 Video ID 格式不正确；模式A只支持单个视频链接。若输入频道链接请切到模式B。")
                    return
                video_ids = [vid]
            else:
                channel_id = resolve_channel_id(user_input, youtube)
                if not channel_id:
                    st.error("无法解析频道信息，请检查 Channel ID 或频道链接是否正确。")
                    return

                published_after = None
                published_before = None

                dr = config["selected_date_range"]
                if (
                    config["enable_date_filter"]
                    and isinstance(dr, (list, tuple))
                    and len(dr) == 2
                ):
                    start_date, end_date = dr
                    if start_date > end_date:
                        start_date, end_date = end_date, start_date

                    start_dt = datetime.combine(start_date, time(0, 0, 0), tzinfo=timezone.utc)
                    end_dt = datetime.combine(end_date, time(23, 59, 59), tzinfo=timezone.utc)

                    published_after = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    published_before = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                video_ids = get_latest_channel_video_ids(
                    youtube,
                    channel_id,
                    max_results=50,
                    published_after=published_after,
                    published_before=published_before,
                )

                if not video_ids:
                    st.error("未获取到该频道的视频，可能频道为空、日期范围无数据或链接有误。")
                    return

            video_items = fetch_videos_details(youtube, video_ids)
            if not video_items:
                st.error("未获取到视频详情，请稍后重试。")
                return

            if config["mode"].startswith("模式 B"):
                vt = config["video_type_filter"]
                filtered = []
                for item in video_items:
                    iso_dur = item.get("contentDetails", {}).get("duration", "PT0S")
                    try:
                        seconds = int(isodate.parse_duration(iso_dur).total_seconds())
                    except Exception:
                        seconds = 0

                    if vt == "仅长视频（>=60秒）" and seconds < 60:
                        continue
                    if vt == "仅 Shorts（<60秒）" and seconds >= 60:
                        continue
                    filtered.append(item)

                video_items = filtered
                if not video_items:
                    st.warning("筛选后没有符合条件的视频。")
                    return

            full_df = build_full_dataframe(video_items, config["selected_fields_keys"])
            list_df = build_list_df(full_df, config["selected_levels"], config["selected_fields_keys"])

            st.session_state.full_df = full_df
            st.session_state.list_df = list_df
            st.session_state.last_run_ok = True

            st.success(f"分析完成！原始 {len(full_df)} 条，筛选后 {len(list_df)} 条。")

    except HttpError as e:
        st.error(human_http_error(e))
    except Exception as e:
        st.error(f"程序运行异常：{e}")


def render_home(config):
    st.markdown('<p class="subtitle-muted">输入视频链接（模式A）或频道链接/ID（模式B）</p>', unsafe_allow_html=True)

    col_input, col_btn = st.columns([8, 2])
    with col_input:
        user_input = st.text_input(
            "请输入链接",
            placeholder="例如：https://www.youtube.com/@VolkaEnglish",
            label_visibility="collapsed",
        )
    with col_btn:
        start_btn = st.button("开始分析", type="primary", use_container_width=True)

    if start_btn:
        run_analysis(config, user_input)

    if st.session_state.last_run_ok and not st.session_state.full_df.empty:
        full_df = st.session_state.full_df
        list_df = st.session_state.list_df

        top_l, top_r = st.columns([4, 1.4])
        with top_l:
            st.markdown("### 竞品视频列表")
        with top_r:
            excel_bytes = to_excel_bytes(full_df)
            st.download_button(
                "下载完整Excel数据",
                data=excel_bytes,
                file_name="youtube_competitor_full.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        chart_df = full_df.copy()
        chart_df["发布日期_dt"] = pd.to_datetime(chart_df["发布时间"], errors="coerce")
        chart_df = chart_df.dropna(subset=["发布日期_dt"]).sort_values("发布日期_dt")
        if not chart_df.empty:
            st.bar_chart(chart_df.set_index("发布日期_dt")["播放量"], color="#FF0000", height=260)

        st.markdown("---")

        if list_df.empty:
            st.info("当前筛选条件下没有视频。")
            return

        st.caption("点击标题进入详情页（Word/PDF 文档式浏览）")
        for i, row in list_df.iterrows():
            date_text = row.get("发布日期", "") or "未知日期"
            title = row.get("标题", "无标题")
            line_prefix = f"{i + 1}、{date_text}, "

            lcol, rcol = st.columns([1.35, 6])
            with lcol:
                st.markdown(line_prefix)
            with rcol:
                if st.button(
                    title,
                    key=f"goto_detail_{int(row['__row_idx__'])}",
                    type="secondary",
                    help="点击进入详情页",
                ):
                    st.session_state.selected_video_idx = int(row["__row_idx__"])
                    st.session_state.page_mode = "detail"
                    st.rerun()


def render_detail():
    if st.button("←", type="tertiary"):
        st.session_state.page_mode = "home"
        st.session_state.selected_video_idx = None
        st.rerun()

    full_df = st.session_state.full_df
    idx = st.session_state.selected_video_idx

    if full_df.empty or idx is None or idx not in full_df.index:
        st.warning("未找到详情数据，请返回主页重新分析。")
        return

    row = full_df.loc[idx]

    c1, c2, c3 = st.columns(3)
    c1.metric("播放量 (Views)", f"{safe_int(row.get('播放量', 0)):,}")
    c2.metric("点赞量 (Likes)", f"{safe_int(row.get('点赞量', 0)):,}")
    c3.metric("互动率 (%)", f"{float(row.get('互动率 (%)', 0.0)):.2f}%")

    st.markdown("---")
    st.markdown(f"### {row.get('标题', '')}")

    thumb = row.get("封面图", "")
    if thumb:
        st.image(thumb, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 描述 (Description)")
    st.markdown(row.get("描述", "") or "（无描述）")

    st.markdown("#### 视频字幕文案 (Transcript)")
    st.markdown(row.get("视频字幕文案", "") or "（无字幕）")

    st.markdown("#### 标签 (Tags)")
    st.markdown(row.get("标签", "") or "（无标签）")


def main():
    inject_global_css()
    init_session_state()
    render_top_banner()

    config = render_sidebar()

    if st.session_state.page_mode == "detail" and st.session_state.selected_video_idx is not None:
        render_detail()
    else:
        st.session_state.page_mode = "home"
        render_home(config)


if __name__ == "__main__":
    main()
