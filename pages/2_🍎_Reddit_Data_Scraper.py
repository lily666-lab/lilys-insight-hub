import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

# 1. 页面基础配置
st.set_page_config(page_title="Reddit 中文学习新帖看板", page_icon="👽", layout="wide")
st.title("👽 Reddit 中文学习新帖看板")

# 2. 侧边栏控制面板
with st.sidebar:
    st.subheader("控制面板")
    days_limit = st.slider("你想抓取最近几天的帖子？", min_value=1, max_value=30, value=11)
    start_btn = st.button("开始抓取", type="primary", use_container_width=True)

# 3. 核心抓取逻辑
if start_btn:
    with st.spinner("正在通过 VIP 通道极速提取数据..."):
        # 目标板块，后面加上了神奇的 .json
        url = "https://www.reddit.com/r/ChineseLanguage/new.json?limit=100"
        
        # 伪装成普通浏览器的头部信息（这是通过保安亭的通行证）
        # 亮明私人专属工具身份，Reddit 反而会放行
     headers = {
         "User-Agent": "python:lilys-insight-hub:v1.0.0 (by /u/lily_creator)"
     }
        
        try:
            # 瞬间发送请求并拿回数据
            response = requests.get(url, headers=headers)
            response.raise_for_status() 
            data = response.json() # 直接解析干净的数据
            
            posts = data['data']['children']
            extracted_data = []
            
            # 计算时间边界
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_limit)
            
            # 整理数据
            for post in posts:
                post_data = post['data']
                created_utc = datetime.fromtimestamp(post_data['created_utc'], tz=timezone.utc)
                
                # 如果帖子太老了，就跳过
                if created_utc < cutoff_time:
                    continue
                    
                extracted_data.append({
                    "标题": post_data.get('title', ''),
                    "发布时间": created_utc.strftime("%Y-%m-%d %H:%M:%S"),
                    "热度 (Upvotes)": post_data.get('score', 0),
                    "评论数": post_data.get('num_comments', 0),
                    "帖子链接": f"https://www.reddit.com{post_data.get('permalink', '')}",
                    "正文片段": post_data.get('selftext', '')[:150] + "..." if post_data.get('selftext') else "（无正文）"
                })
            
            # 4. 展示结果
            if extracted_data:
                df = pd.DataFrame(extracted_data)
                st.success(f"🎉 抓取成功！瞬间获取到 {len(df)} 条符合条件的帖子。")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("通道已连接，但在这个天数范围内没有找到新帖子哦。")
                
        except Exception as e:
            st.error(f"请求被拦截或出现网络问题: {e}")
