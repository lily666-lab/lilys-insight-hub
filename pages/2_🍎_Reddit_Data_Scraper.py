import csv
import io
import random
import re
import shutil
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

import streamlit as st
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_TARGET = "ChineseLanguage"
MAX_POSTS = 300
REDDIT_HOSTS = {"reddit.com", "www.reddit.com", "old.reddit.com"}


st.set_page_config(
    page_title="Reddit Insight Harvester",
    page_icon="R",
    layout="wide",
)


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --paper: #f7f4ee;
            --ink: #1f2933;
            --muted: #667085;
            --line: #ded7cc;
            --accent: #d9480f;
            --accent-dark: #a83508;
            --green: #1f7a5a;
        }
        .stApp {
            color: var(--ink);
            background:
                radial-gradient(circle at 12% 5%, rgba(217, 72, 15, .11), transparent 24rem),
                linear-gradient(180deg, #fbfaf7 0%, var(--paper) 100%);
        }
        [data-testid="stHeader"] {
            display: none;
        }
        [data-testid="stAppViewContainer"] > .main {
            padding-top: 0;
        }
        [data-testid="stMainBlockContainer"] {
            padding-top: 1.25rem;
        }
        [data-testid="stSidebar"] {
            background: #fffaf2;
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebarContent"] {
            padding-top: 1.25rem;
        }
        [data-testid="stSidebarHeader"] {
            position: absolute;
            inset: .5rem .5rem auto auto;
            z-index: 2;
            height: auto;
        }
        .hero {
            padding: 0 0 1rem;
            border-bottom: 1px solid var(--line);
            margin-bottom: 1.2rem;
        }
        .hero h1 {
            margin: 0;
            font-size: clamp(2.2rem, 4vw, 4.5rem);
            line-height: .96;
            letter-spacing: 0;
        }
        .metric-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .75rem;
            margin: .8rem 0 1.2rem;
        }
        .metric {
            border: 1px solid var(--line);
            background: rgba(255,255,255,.72);
            border-radius: 8px;
            padding: .85rem .95rem;
        }
        .metric strong {
            display: block;
            font-size: 1.35rem;
            line-height: 1.1;
        }
        .metric span {
            color: var(--muted);
            font-size: .82rem;
        }
        .post-card {
            min-height: 260px;
            border: 1px solid var(--line);
            background: rgba(255,255,255,.82);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: .85rem;
            box-shadow: 0 12px 28px rgba(31, 41, 51, .06);
        }
        .post-meta {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-bottom: .65rem;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            min-height: 1.5rem;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: .1rem .55rem;
            color: var(--muted);
            background: #fffaf2;
            font-size: .75rem;
            white-space: nowrap;
        }
        .score {
            color: #fff;
            background: var(--accent);
            border-color: var(--accent);
            font-weight: 700;
        }
        .post-card h3 {
            margin: 0 0 .5rem;
            font-size: 1.02rem;
            line-height: 1.35;
            letter-spacing: 0;
        }
        .post-card p {
            color: #46515c;
            line-height: 1.48;
            font-size: .9rem;
            margin-bottom: .8rem;
        }
        .post-card a {
            color: var(--accent-dark);
            font-weight: 700;
            text-decoration: none;
        }
        .stButton button, .stDownloadButton button {
            border-radius: 8px;
            font-weight: 700;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }
        @media (max-width: 760px) {
            .metric-strip { grid-template-columns: 1fr; }
            .post-card { min-height: auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def normalize_target(raw_target: str) -> tuple[str, str]:
    target = (raw_target or "").strip()
    if not target:
        target = DEFAULT_TARGET

    if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_]{1,20}", target):
        subreddit = target
        return f"https://old.reddit.com/r/{subreddit}/new/", f"r/{subreddit}"

    if target.startswith("r/"):
        subreddit = target.split("/", 1)[1].strip("/")
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_]{1,20}", subreddit):
            raise ValueError("Subreddit 名称只能包含字母、数字和下划线。")
        return f"https://old.reddit.com/r/{subreddit}/new/", f"r/{subreddit}"

    if not target.startswith(("http://", "https://")):
        raise ValueError("请输入 subreddit 名称、r/名称，或完整 Reddit 链接。")

    parsed = urlparse(target)
    host = parsed.netloc.lower()
    if host not in REDDIT_HOSTS:
        raise ValueError("当前爬虫只支持 Reddit 页面。可以输入 reddit.com 或 old.reddit.com 链接。")

    clean_path = parsed.path or "/"
    if not clean_path.startswith("/r/"):
        raise ValueError("请输入某个 subreddit 的列表页链接，例如 https://www.reddit.com/r/ChineseLanguage/new/。")

    old_url = urlunparse(("https", "old.reddit.com", clean_path, "", parsed.query, ""))
    label_parts = clean_path.strip("/").split("/")
    label = f"r/{label_parts[1]}" if len(label_parts) >= 2 else "Reddit"
    return old_url, label


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return f"https://old.reddit.com{url}"


def parse_utc_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def clean_text(text: str | None) -> str:
    return " ".join((text or "").split())


def shorten(text: str, max_len: int = 160) -> str:
    clean = clean_text(text)
    if len(clean) <= max_len:
        return clean
    return f"{clean[:max_len].rstrip()}..."


def safe_score(raw_score: str | None) -> str:
    score = clean_text(raw_score)
    if not score or score in {"•", "score hidden"}:
        return "0"
    return score


def to_csv_bytes(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO()
    fields = ["score", "title", "content", "datetime", "post_url", "source", "domain"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return output.getvalue().encode("utf-8-sig")


def scrape_old_reddit(
    target_url: str,
    days_limit: int,
    max_posts: int = MAX_POSTS,
    sort_mode: str = "new",
    headless: bool = True,
) -> tuple[list[dict[str, str]], str]:
    normalized_url = with_sort_mode(target_url, sort_mode)
    posts: list[dict[str, str]] = []
    now_utc = datetime.now(timezone.utc)
    max_delta = timedelta(days=days_limit)
    seen_urls: set[str] = set()
    next_page_url = normalized_url
    hit_time_boundary = False

    with sync_playwright() as playwright:
        chromium_path = (
            shutil.which("chromium")
            or shutil.which("chromium-browser")
            or shutil.which("google-chrome")
        )
        launch_options = {
            "headless": headless,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }
        if chromium_path:
            launch_options["executable_path"] = chromium_path

        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 1100},
        )
        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in {"font", "image", "media", "stylesheet"}
            else route.continue_(),
        )
        page = context.new_page()

        try:
            while next_page_url and len(posts) < max_posts and not hit_time_boundary:
                page.goto(next_page_url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_selector("div.thing", timeout=20_000)
                wait_like_a_person(page)

                things = page.locator("div.thing")
                total = things.count()
                if total == 0:
                    break

                for idx in range(total):
                    if len(posts) >= max_posts:
                        break

                    thing = things.nth(idx)
                    if thing.get_attribute("data-promoted") == "true":
                        continue

                    title_node = thing.locator("a.title").first
                    time_node = thing.locator("time.live-timestamp").first
                    raw_time = time_node.get_attribute("datetime") if time_node.count() else None
                    post_dt = parse_utc_datetime(raw_time)
                    if post_dt and now_utc - post_dt > max_delta:
                        hit_time_boundary = True
                        break

                    try:
                        title = clean_text(title_node.inner_text(timeout=4_000)) if title_node.count() else ""
                    except PlaywrightTimeoutError:
                        title = ""

                    post_url = normalize_url(title_node.get_attribute("href")) if title_node.count() else ""
                    if not post_url or post_url in seen_urls:
                        continue
                    seen_urls.add(post_url)

                    score_node = thing.locator("div.score.unvoted").first
                    score_text = safe_score(score_node.inner_text(timeout=2_000) if score_node.count() else "")

                    body_node = thing.locator("div.expando div.usertext-body div.md").first
                    try:
                        summary_text = clean_text(body_node.inner_text(timeout=2_000)) if body_node.count() else ""
                    except PlaywrightTimeoutError:
                        summary_text = ""

                    domain_node = thing.locator("span.domain a").first
                    domain = clean_text(domain_node.inner_text(timeout=2_000)) if domain_node.count() else ""

                    posts.append(
                        {
                            "score": score_text,
                            "title": title,
                            "content": summary_text,
                            "datetime": post_dt.isoformat() if post_dt else "",
                            "post_url": post_url,
                            "source": normalized_url,
                            "domain": domain,
                        }
                    )

                if hit_time_boundary or len(posts) >= max_posts:
                    break

                next_node = page.locator("span.next-button a").first
                next_page_url = normalize_url(next_node.get_attribute("href")) if next_node.count() else ""
                wait_like_a_person(page, 0.8, 1.6)

        except PlaywrightTimeoutError:
            return posts, "页面加载超时。Reddit 可能限流、网络不稳定，或这个页面没有 old Reddit 列表结构。"
        except PlaywrightError as exc:
            return posts, f"Playwright 抓取失败：{exc}"
        finally:
            context.close()
            browser.close()

    if posts:
        boundary_note = "，已到达时间边界" if hit_time_boundary else ""
        return posts, f"抓取完成：共 {len(posts)} 条{boundary_note}。"
    return posts, "没有抓到帖子。请确认链接是公开 subreddit 列表页，或放宽时间范围。"


def with_sort_mode(target_url: str, sort_mode: str) -> str:
    parsed = urlparse(target_url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "r":
        subreddit = parts[1]
        suffix = sort_mode if sort_mode in {"new", "hot", "top", "rising"} else "new"
        path = f"/r/{subreddit}/{suffix}/"
        return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))
    return target_url


def wait_like_a_person(page, min_seconds: float = 0.7, max_seconds: float = 1.4) -> None:
    page.wait_for_timeout(random.uniform(min_seconds, max_seconds) * 1000)


def render_cards(rows: list[dict[str, str]], columns_count: int = 3) -> None:
    cols = st.columns(columns_count)
    for idx, item in enumerate(rows):
        with cols[idx % columns_count]:
            title = clean_text(item.get("title")) or "无标题"
            content = shorten(item.get("content", ""), 180) or "无正文摘要"
            score = item.get("score", "0")
            published = item.get("datetime", "未知")
            domain = item.get("domain", "reddit")
            url = item.get("post_url", "")
            st.markdown(
                f"""
                <article class="post-card">
                    <div class="post-meta">
                        <span class="pill score">score {escape_html(score)}</span>
                        <span class="pill">{escape_html(domain)}</span>
                    </div>
                    <h3>{escape_html(title)}</h3>
                    <p>{escape_html(content)}</p>
                    <div class="post-meta"><span class="pill">{escape_html(published)}</span></div>
                    <a href="{escape_html(url)}" target="_blank" rel="noreferrer">Open Reddit</a>
                </article>
                """,
                unsafe_allow_html=True,
            )


def escape_html(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def init_state() -> None:
    defaults = {
        "rows": [],
        "notice": "",
        "target_label": "r/ChineseLanguage",
        "target_url": "https://old.reddit.com/r/ChineseLanguage/new/",
        "days_limit": 1,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def main() -> None:
    inject_theme()
    init_state()

    st.markdown(
        """
        <section class="hero">
            <h1>Reddit Insight Harvester</h1>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("抓取设置")
        raw_target = st.text_input(
            "Subreddit 或 Reddit 链接",
            value=DEFAULT_TARGET,
            placeholder="ChineseLanguage / r/China / https://www.reddit.com/r/China/new/",
        )
        sort_mode = st.segmented_control(
            "排序",
            options=["new", "hot", "top", "rising"],
            default="new",
        )
        days_limit = st.slider("最近几天", min_value=1, max_value=90, value=1)
        max_posts = st.slider("最多抓取", min_value=10, max_value=MAX_POSTS, value=80, step=10)
        show_table = st.toggle("显示表格", value=True)
        start = st.button("开始抓取", type="primary", use_container_width=True)

        st.caption("提示：当前爬虫使用 old.reddit.com 的公开页面结构，不需要 Reddit API。")

    if start:
        try:
            target_url, target_label = normalize_target(raw_target)
        except ValueError as exc:
            st.error(str(exc))
            return

        with st.spinner(f"正在抓取 {target_label} ..."):
            rows, notice = scrape_old_reddit(
                target_url=target_url,
                days_limit=days_limit,
                max_posts=max_posts,
                sort_mode=sort_mode,
            )
        st.session_state.rows = rows
        st.session_state.notice = notice
        st.session_state.target_label = target_label
        st.session_state.target_url = with_sort_mode(target_url, sort_mode)
        st.session_state.days_limit = days_limit

    rows = st.session_state.rows
    notice = st.session_state.notice

    if notice:
        if rows:
            st.success(notice)
        else:
            st.warning(notice)

    st.markdown(
        f"""
        <div class="metric-strip">
            <div class="metric"><strong>{len(rows)}</strong><span>已抓取帖子</span></div>
            <div class="metric"><strong>{escape_html(st.session_state.target_label)}</strong><span>当前来源</span></div>
            <div class="metric"><strong>{st.session_state.days_limit}d</strong><span>时间范围</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if rows:
        csv_data = to_csv_bytes(rows)
        file_date = datetime.now().strftime("%Y%m%d")
        safe_label = re.sub(r"[^A-Za-z0-9_]+", "_", st.session_state.target_label).strip("_")
        st.download_button(
            "下载 CSV",
            data=csv_data,
            file_name=f"reddit_{safe_label}_{file_date}_{st.session_state.days_limit}d.csv",
            mime="text/csv",
            use_container_width=False,
        )

        tabs = st.tabs(["卡片预览", "数据表"])
        with tabs[0]:
            render_cards(rows, columns_count=3)
        with tabs[1]:
            if show_table:
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("表格已在左侧关闭。")
    else:
        st.info("在左侧输入 subreddit 或 Reddit 链接，然后点击“开始抓取”。")


if __name__ == "__main__":
    main()
