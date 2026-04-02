import csv
import io
import random
from datetime import datetime, timedelta, timezone

import streamlit as st
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

TARGET_URL = "https://old.reddit.com/r/ChineseLanguage/new/"
MAX_POSTS = 200


def rand_sleep(page, min_seconds: float = 1.0, max_seconds: float = 2.0) -> None:
    page.wait_for_timeout(random.uniform(min_seconds, max_seconds) * 1000)


def normalize_url(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
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


def shorten(text: str, max_len: int = 80) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= max_len:
        return clean
    return f"{clean[:max_len]}..."


def to_csv_bytes(rows: list[dict[str, str]]) -> bytes:
    output = io.StringIO()
    fields = ["score", "title", "content", "datetime", "post_url"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return output.getvalue().encode("utf-8-sig")


def scrape_old_reddit(days_limit: int, max_posts: int = MAX_POSTS) -> tuple[list[dict[str, str]], str]:
    posts: list[dict[str, str]] = []
    notice = ""
    now_utc = datetime.now(timezone.utc)
    max_delta = timedelta(days=days_limit)
    seen_urls: set[str] = set()
    next_page_url = TARGET_URL
    hit_time_boundary = False
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        blocked = {"image", "media", "font", "stylesheet"}
        context.route(
            "**/*",
            lambda route: route.abort() if route.request.resource_type in blocked else route.continue_(),
        )
        page = context.new_page()
        try:
            while next_page_url and len(posts) < max_posts and not hit_time_boundary:
                page.goto(next_page_url, wait_until="domcontentloaded", timeout=45000)
                rand_sleep(page)
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
                    if title_node.count() == 0:
                        continue
                    title = title_node.inner_text(timeout=1500).strip()
                    post_url = normalize_url(title_node.get_attribute("href"))
                    if not post_url or post_url in seen_urls:
                        continue
                    time_node = thing.locator("time.live-timestamp").first
                    raw_time = ""
                    if time_node.count() > 0:
                        raw_time = (
                            time_node.get_attribute("datetime")
                            or time_node.get_attribute("title")
                            or time_node.inner_text(timeout=1000).strip()
                        )
                    post_dt = parse_utc_datetime(raw_time)
                    if post_dt and now_utc - post_dt > max_delta:
                        hit_time_boundary = True
                        break
                    score_text = thing.get_attribute("data-score") or "0"
                    score_node = thing.locator("div.score.unvoted").first
                    if (not score_text or score_text == "0") and score_node.count() > 0:
                        score_text = score_node.inner_text(timeout=1200).strip() or "0"
                    summary_text = ""
                    body_node = thing.locator("div.expando div.usertext-body div.md").first
                    if body_node.count() > 0:
                        summary_text = body_node.inner_text(timeout=1200).strip()
                    if not summary_text:
                        domain_node = thing.locator("span.domain a").first
                        if domain_node.count() > 0:
                            summary_text = domain_node.inner_text(timeout=1000).strip()
                    if not summary_text:
                        summary_text = thing.get_attribute("data-domain") or ""
                    posts.append(
                        {
                            "score": score_text,
                            "title": title,
                            "content": summary_text,
                            "datetime": post_dt.isoformat() if post_dt else (raw_time or "未知"),
                            "post_url": post_url,
                        }
                    )
                    seen_urls.add(post_url)
                if hit_time_boundary or len(posts) >= max_posts:
                    break
                next_node = page.locator("span.next-button a").first
                if next_node.count() == 0:
                    break
                next_page_url = normalize_url(next_node.get_attribute("href"))
                if not next_page_url:
                    break
                rand_sleep(page)
            if not posts:
                notice = "页面已打开，但没有提取到符合条件的帖子。"
            elif len(posts) >= max_posts:
                notice = f"已达到安全上限 {max_posts} 条，抓取已停止。"
            elif hit_time_boundary:
                notice = f"已到达超过最近 {days_limit} 天的帖子，抓取已停止。"
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            notice = f"抓取失败：{exc}"
        finally:
            context.close()
            browser.close()
    return posts, notice


def render_cards(rows: list[dict[str, str]], columns_count: int = 3) -> None:
    cols = st.columns(columns_count)
    for idx, item in enumerate(rows):
        with cols[idx % columns_count]:
            with st.container(border=True):
                st.markdown(f"**🔥 热度：{item.get('score', '0')}**")
                st.markdown(f"**{item.get('title', '').strip() or '（无标题）'}**")
                st.write(shorten(item.get("content", ""), 80) or "（无摘要）")
                st.caption(f"发布时间：{item.get('datetime', '未知')}")
                url = item.get("post_url", "")
                if url:
                    st.link_button("去 Reddit 围观", url, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="📺 Reddit 中文学习新帖看板", layout="wide")
    st.title("📺 Reddit 中文学习新帖看板")

    if "rows" not in st.session_state:
        st.session_state.rows = []
    if "notice" not in st.session_state:
        st.session_state.notice = ""
    if "days_limit" not in st.session_state:
        st.session_state.days_limit = 1

    with st.sidebar:
        st.subheader("控制面板")
        days_limit = st.slider("你想抓取最近几天的帖子？", min_value=1, max_value=30, value=1)
        start = st.button("开始抓取", type="primary", use_container_width=True)

    if start:
        with st.spinner("正在抓取 old Reddit 新帖列表..."):
            rows, notice = scrape_old_reddit(days_limit=days_limit, max_posts=MAX_POSTS)
            st.session_state.rows = rows
            st.session_state.notice = notice
            st.session_state.days_limit = days_limit

    rows = st.session_state.rows
    notice = st.session_state.notice

    if notice:
        if rows:
            st.info(notice)
        else:
            st.warning(notice)

    if rows:
        csv_data = to_csv_bytes(rows)
        file_date = datetime.now().strftime("%Y%m%d")
        st.download_button(
            "下载 CSV",
            data=csv_data,
            file_name=f"reddit_chinese_new_{file_date}_{st.session_state.days_limit}d.csv",
            mime="text/csv",
        )
        st.write(f"已抓取 {len(rows)} 条帖子（安全上限 {MAX_POSTS}）")
        render_cards(rows, columns_count=3)
    else:
        st.info("在左侧选择天数后，点击“开始抓取”。")


if __name__ == "__main__":
    main()
