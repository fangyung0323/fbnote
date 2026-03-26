#!/usr/bin/env python3
"""
每日自動發文機器人
- 使用 DeepSeek API 生成文章（四大類別輪換：植物、永續、碳盤查、生活）
- 將文章保存為 HTML
- 推送到網站倉庫的 daily-post 目錄
- 自動生成套用官網模板的索引頁面
"""

import os
import sys
import json
import subprocess
import shutil
import tempfile
import re
from datetime import datetime
import requests

# ==================== 配置 ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 四大類別
CATEGORIES = ["植物", "永續", "碳盤查", "生活"]

# 類別對應的顏色（用於頁面顯示）
CATEGORY_COLORS = {
    "植物": "#4a7c59",
    "永續": "#2c7a4d",
    "碳盤查": "#1e6f5c",
    "生活": "#b88b4a"
}

# 各類別的提示詞模板
PROMPT_TEMPLATES = {
    "植物": """請寫一篇關於「植物」的科普或生活文章，主題可以圍繞：
- 植物的生態特徵與魅力
- 室內植物養護技巧
- 特殊植物品種介紹
- 植物與身心靈健康

要求：
1. 標題要吸引人
2. 內容約 500-800 字
3. 語言使用繁體中文
4. 結尾加上「🌿 蕨積 - 讓生活多一點綠」""",

    "永續": """請寫一篇關於「永續發展」或「環境永續」的文章，主題可以圍繞：
- 日常生活中的永續實踐
- 減塑與零浪費生活
- 永續消費與循環經濟
- 企業永續案例或趨勢

要求：
1. 標題要吸引人
2. 內容約 500-800 字
3. 語言使用繁體中文
4. 結尾加上「🌿 蕨積 - 讓生活多一點綠」""",

    "碳盤查": """請寫一篇關於「碳盤查」或「碳管理」的科普文章，主題可以圍繞：
- 碳盤查的基本概念與方法
- 企業為何需要碳盤查
- 個人碳足跡計算與減碳
- 碳中和與淨零排放趨勢

要求：
1. 標題要吸引人
2. 內容約 500-800 字
3. 語言使用繁體中文
4. 結尾加上「🌿 蕨積 - 讓生活多一點綠」""",

    "生活": """請寫一篇關於「生活風格」或「質感生活」的文章，主題可以圍繞：
- 慢生活與正念練習
- 居家佈置與收納美學
- 簡單生活與斷捨離
- 生活儀式感與幸福感

要求：
1. 標題要吸引人
2. 內容約 500-800 字
3. 語言使用繁體中文
4. 結尾加上「🌿 蕨積 - 讓生活多一點綠」"""
}

# 各類別的 System Prompt
SYSTEM_PROMPTS = {
    "植物": "你是一位植物學科普作家，擅長撰寫有趣且專業的植物文章。",
    "永續": "你是一位環境永續專家，擅長用淺顯易懂的方式講解永續議題。",
    "碳盤查": "你是一位碳管理顧問，擅長解釋碳盤查與氣候變遷相關知識。",
    "生活": "你是一位生活風格作家，擅長分享質感生活與心靈成長的內容。"
}

def get_today_category():
    """根據日期決定今天的主題類別（四個類別輪換）"""
    day_of_year = datetime.now().timetuple().tm_yday
    category_index = (day_of_year - 1) % len(CATEGORIES)
    return CATEGORIES[category_index]

# ==================== 文章生成 ====================
def generate_article():
    """调用 DeepSeek API 生成文章内容"""
    if not DEEPSEEK_API_KEY:
        print("❌ 錯誤：DEEPSEEK_API_KEY 環境變數未設定")
        return None, None, None
    
    category = get_today_category()
    prompt = PROMPT_TEMPLATES[category]
    
    print(f"📌 今日主題類別：{category}")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPTS[category]},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }
    
    print("🤖 正在呼叫 DeepSeek API 生成文章...")
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        lines = content.strip().split("\n")
        title = lines[0].replace("#", "").strip()
        if not title:
            title = f"{category}日誌 {datetime.now().strftime('%Y-%m-%d')}"
        
        print(f"✅ 文章生成成功：{title}")
        print(f"📂 類別：{category}")
        return title, content, category
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None, None, None

def save_article_as_html(title, content, category, output_dir="articles"):
    """將文章儲存為 HTML 檔案"""
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = title.replace(" ", "-").replace("/", "-").replace("?", "").replace("！", "")[:50]
    filename = f"{date_str}-{safe_title}.html"
    filepath = os.path.join(output_dir, filename)
    
    category_color = CATEGORY_COLORS.get(category, "#4a7c59")
    
    # 將換行轉換為 <br>，同時保留段落結構
    content_html = content.replace(chr(10), "<br>")
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 蕨積每日文章</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.8;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            background: #faf8f4;
            color: #2c3e2f;
        }}
        .category-tag {{
            display: inline-block;
            background: {category_color};
            color: white;
            padding: 0.2rem 0.8rem;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-bottom: 1rem;
        }}
        h1 {{ color: #2c5e2e; border-left: 4px solid #6b8c5c; padding-left: 1rem; margin: 1rem 0; }}
        .date {{ color: #7f8c6d; margin-bottom: 2rem; }}
        .content {{ margin: 2rem 0; }}
        .content p {{ margin: 1rem 0; }}
        hr {{ margin: 2rem 0; border: none; border-top: 1px solid #e0d6cc; }}
        .footer {{ text-align: center; margin-top: 3rem; color: #7f8c6d; font-size: 0.9rem; }}
        .back-link {{
            display: inline-block;
            margin-top: 1rem;
            color: #4a7c59;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="category-tag">📌 {category}</div>
    <h1>{title}</h1>
    <div class="date">📅 {datetime.now().strftime("%Y年%m月%d日")}</div>
    <div class="content">
        {content_html}
    </div>
    <hr>
    <div class="footer">
        🌿 蕨積 - 讓生活多一點綠<br>
        每日一篇，與你一起成長
    </div>
    <a href="index.html" class="back-link">← 返回文章列表</a>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"📄 文章已儲存：{filepath}")
    return filepath

# ==================== 索引頁面生成（套用官網模板） ====================
def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面
    套用蕨積官網模板風格，最新文章完整顯示，右邊過往文章歸檔
    """
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html":
            filepath = os.path.join(daily_post_dir, file)
            
            category = "未分類"
            title = ""
            content_html = ""
            date_str = file[:10] if len(file) >= 10 else "0000-00-00"
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    full_content = f.read()
                    
                    match_cat = re.search(r'<div class="category-tag">📌 (.+?)</div>', full_content)
                    if match_cat:
                        category = match_cat.group(1)
                    
                    match_title = re.search(r'<h1>(.+?)</h1>', full_content)
                    if match_title:
                        title = match_title.group(1)
                    
                    match_content = re.search(r'<div class="content">(.*?)</div>', full_content, re.DOTALL)
                    if match_content:
                        content_html = match_content.group(1)
            except:
                pass
            
            articles.append({
                "filename": file,
                "date": date_str,
                "title": title,
                "category": category,
                "content": content_html
            })
    
    articles.sort(key=lambda x: x["date"], reverse=True)
    
    if not articles:
        return
    
    latest = articles[0]
    past_articles = articles[1:]
    
    # 按年月歸檔過往文章
    archive_by_month = {}
    for article in past_articles:
        month_key = article["date"][:7]
        if month_key not in archive_by_month:
            archive_by_month[month_key] = []
        archive_by_month[month_key].append(article)
    
    # ========== 套用模板的 HTML ==========
    index_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>蕨積每日文章 — 植物・永續・碳盤查・生活</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600;900&family=Noto+Sans+TC:wght@300;400;500&family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lucide@latest"></script>
  <style>
    /* ===== 共用樣式 ===== */
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    :root {{
      --ink: #1a1a14;
      --moss: #3d5a38;
      --fern: #5a7a4a;
      --sage: #8aab7a;
      --mist: #d4e4c8;
      --cream: #f5f0e8;
      --stone: #9a9080;
      --paper: #faf7f2;
    }}
    body {{
      font-family: 'Noto Sans TC', sans-serif;
      background: var(--paper);
      color: var(--ink);
      overflow-x: hidden;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    nav {{
      position: fixed; top: 0; left: 0; right: 0; z-index: 100;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 4vw; height: 72px;
      background: rgba(250,247,242,0.92);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(90,122,74,0.12);
    }}
    nav.scrolled {{ box-shadow: 0 2px 24px rgba(61,90,56,0.10); }}

    .logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; flex-shrink: 0; }}
    .logo-mark {{ width: 38px; height: 38px; flex-shrink: 0; }}
    .logo-mark img {{ width: 100%; height: 100%; object-fit: contain; display: block; }}
    .logo-text {{
      font-family: 'Noto Serif TC', serif;
      font-weight: 900;
      font-size: 1.35rem;
      color: var(--moss);
      letter-spacing: 0.05em;
      line-height: 1;
      white-space: nowrap;
    }}
    .logo-text span {{
      display: block;
      font-family: 'Cormorant Garamond', serif;
      font-weight: 300;
      font-size: 0.65rem;
      letter-spacing: 0.25em;
      color: var(--stone);
      margin-top: 2px;
    }}

    .nav-links {{
      display: flex;
      gap: 2rem;
      list-style: none;
      align-items: center;
      white-space: nowrap;
    }}
    .nav-links li {{ position: relative; padding: 0 2px; }}
    .nav-links a {{
      font-family: 'Noto Sans TC', sans-serif;
      font-size: 0.82rem;
      font-weight: 400;
      letter-spacing: 0.1em;
      color: var(--ink);
      text-decoration: none;
      padding-bottom: 3px;
      opacity: 0.75;
      display: inline-block;
    }}
    .nav-links a:hover {{ opacity: 1; color: var(--fern); }}
    .nav-contact {{
      padding: 8px 20px !important;
      border: 1px solid var(--fern) !important;
      border-radius: 2px;
      color: var(--fern) !important;
      opacity: 1 !important;
      margin-left: 0.5rem;
    }}
    .nav-contact:hover {{ background: var(--fern); color: white !important; }}
    .has-dropdown > a::after {{ display: none; }}

    .nav-links li .dropdown {{
      display: none;
      position: absolute;
      top: calc(100% + 18px);
      left: 50%;
      transform: translateX(-50%);
      background: rgba(250,247,242,0.98);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(90,122,74,0.14);
      border-top: 2px solid var(--fern);
      box-shadow: 0 12px 40px rgba(61,90,56,0.12);
      min-width: 148px;
      list-style: none;
      padding: 8px 0;
      z-index: 300;
    }}
    .nav-links li:hover .dropdown,
    .nav-links li:focus-within .dropdown {{ display: block; }}
    .nav-links li .dropdown::before {{
      content: '';
      position: absolute;
      top: -7px;
      left: 50%;
      transform: translateX(-50%);
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-bottom: 6px solid var(--fern);
    }}
    .dropdown li a {{
      display: block;
      padding: 10px 20px;
      font-size: 0.78rem;
      font-weight: 400;
      letter-spacing: 0.08em;
      color: var(--ink);
      opacity: 0.7;
      white-space: nowrap;
      text-decoration: none;
    }}
    .dropdown li a:hover {{
      opacity: 1;
      color: var(--fern);
      padding-left: 26px;
      background: rgba(90,122,74,0.04);
    }}
    .dropdown li + li {{ border-top: 1px solid rgba(90,122,74,0.08); }}

    .hamburger {{
      display: none;
      flex-direction: column;
      justify-content: center;
      gap: 6px;
      width: 40px; height: 40px;
      cursor: pointer;
      background: none; border: none;
      flex-shrink: 0;
    }}
    .hamburger span {{
      display: block;
      width: 24px; height: 1.5px;
      background: var(--moss);
      transition: transform 0.2s ease;
    }}
    .hamburger.open span:nth-child(1) {{ transform: translateY(7.5px) rotate(45deg); }}
    .hamburger.open span:nth-child(2) {{ opacity: 0; }}
    .hamburger.open span:nth-child(3) {{ transform: translateY(-7.5px) rotate(-45deg); }}

    .mobile-menu {{
      position: fixed; top: 72px; left: 0; right: 0; bottom: 0;
      background: #faf7f2;
      border-bottom: 1px solid rgba(90,122,74,0.15);
      padding: 0 6vw 40px;
      z-index: 99;
      overflow-y: auto;
      transform: translateX(100%);
      visibility: hidden;
      transition: transform 0.3s ease;
    }}
    .mobile-menu.open {{ transform: translateX(0); visibility: visible; }}
    .mobile-menu ul {{ list-style: none; }}
    .mobile-menu > ul > li > a,
    .mobile-parent {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 0;
      font-family: 'Noto Serif TC', serif;
      font-weight: 600;
      font-size: 1rem;
      letter-spacing: 0.08em;
      color: var(--moss);
      text-decoration: none;
      border-bottom: 1px solid rgba(90,122,74,0.1);
      cursor: pointer;
    }}
    .mobile-parent:hover, .mobile-menu > ul > li > a:hover {{ color: var(--fern); }}
    .mobile-caret {{ display: inline-block; transition: transform 0.2s; }}
    .mobile-caret.open {{ transform: rotate(180deg); }}
    .mobile-sub {{
      list-style: none;
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.3s ease;
    }}
    .mobile-sub.open {{ max-height: 200px; }}
    .mobile-sub li a {{
      display: block;
      padding: 11px 0 11px 16px;
      font-size: 0.85rem;
      color: var(--stone);
      text-decoration: none;
      border-bottom: 1px solid rgba(90,122,74,0.06);
      letter-spacing: 0.06em;
    }}
    .mobile-sub li a:hover {{ color: var(--fern); }}

    @media (max-width: 768px) {{
      .nav-links {{ display: none; }}
      .hamburger {{ display: flex; }}
    }}

    /* ===== 頁面內容區域 ===== */
    .content {{
      flex: 1;
      padding-top: 92px;
      padding-bottom: 40px;
    }}
    .daily-container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 2rem;
    }}
    .page-header {{
      text-align: center;
      margin-bottom: 2rem;
    }}
    .page-header h1 {{
      color: var(--moss);
      font-size: 2rem;
      font-family: 'Noto Serif TC', serif;
    }}
    .page-header p {{
      color: var(--stone);
      margin-top: 0.5rem;
    }}
    /* 兩欄布局 */
    .two-columns {{
      display: flex;
      gap: 2rem;
      flex-wrap: wrap;
    }}
    .main-col {{
      flex: 3;
      min-width: 250px;
    }}
    .sidebar-col {{
      flex: 1;
      min-width: 200px;
      background: white;
      border-radius: 16px;
      padding: 1.5rem;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
      height: fit-content;
      border: 1px solid rgba(90,122,74,0.1);
    }}
    .section-title {{
      font-size: 1.2rem;
      color: var(--moss);
      border-bottom: 2px solid #e0d6cc;
      padding-bottom: 0.5rem;
      margin-bottom: 1rem;
      font-family: 'Noto Serif TC', serif;
    }}
    /* 最新文章完整顯示 */
    .latest-article {{
      background: white;
      border-radius: 16px;
      padding: 2rem;
      margin-bottom: 2rem;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      border: 1px solid rgba(90,122,74,0.1);
    }}
    .latest-category {{
      display: inline-block;
      background: {CATEGORY_COLORS.get(latest['category'], '#6c757d')};
      color: white;
      padding: 0.2rem 0.8rem;
      border-radius: 20px;
      font-size: 0.8rem;
      margin-bottom: 1rem;
    }}
    .latest-title {{
      font-size: 1.8rem;
      color: var(--moss);
      margin-bottom: 0.5rem;
      font-family: 'Noto Serif TC', serif;
    }}
    .latest-date {{
      color: var(--stone);
      margin-bottom: 1.5rem;
      font-size: 0.9rem;
    }}
    .latest-content {{
      line-height: 1.8;
      color: var(--ink);
    }}
    .latest-content p {{
      margin: 1rem 0;
    }}
    .read-more {{
      display: inline-block;
      margin-top: 1rem;
      color: var(--fern);
      text-decoration: none;
      font-weight: 500;
    }}
    /* 過往文章列表 */
    .past-list {{
      list-style: none;
      padding: 0;
    }}
    .past-item {{
      margin-bottom: 1rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #f0e8e0;
    }}
    .past-link {{
      font-size: 0.95rem;
      font-weight: 500;
      color: var(--fern);
      text-decoration: none;
      display: block;
    }}
    .past-link:hover {{
      text-decoration: underline;
    }}
    .past-meta {{
      font-size: 0.7rem;
      color: #aaa;
      margin-top: 0.25rem;
    }}
    .past-badge {{
      display: inline-block;
      font-size: 0.65rem;
      padding: 0.1rem 0.5rem;
      border-radius: 12px;
      color: white;
      margin-right: 0.5rem;
    }}
    .archive-month {{
      margin-bottom: 1rem;
    }}
    .archive-month-title {{
      font-weight: 600;
      color: var(--moss);
      margin-bottom: 0.5rem;
    }}
    .archive-list {{
      list-style: none;
      padding-left: 0.5rem;
    }}
    .archive-list li {{
      margin-bottom: 0.3rem;
    }}
    .archive-list a {{
      color: var(--stone);
      text-decoration: none;
      font-size: 0.85rem;
    }}
    .archive-list a:hover {{
      color: var(--fern);
      text-decoration: underline;
    }}
    footer {{
      border-top: 1px solid rgba(90,122,74,0.15);
      padding: 40px 4vw;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--paper);
      margin-top: auto;
    }}
    .footer-links {{
      display: flex;
      gap: 24px;
      list-style: none;
    }}
    .footer-links a {{
      font-size: 0.75rem;
      color: var(--stone);
      text-decoration: none;
      letter-spacing: 0.08em;
      opacity: 0.7;
    }}
    .footer-links a:hover {{
      opacity: 1;
      color: var(--fern);
    }}
    .footer-copy {{
      font-size: 0.75rem;
      color: var(--stone);
      letter-spacing: 0.1em;
    }}
    @media (max-width: 768px) {{
      .daily-container {{ padding: 0 1rem; }}
      .two-columns {{ flex-direction: column; }}
      .latest-title {{ font-size: 1.4rem; }}
      footer {{
        flex-direction: column;
        gap: 20px;
        text-align: center;
      }}
      .footer-links {{
        justify-content: center;
        flex-wrap: wrap;
      }}
    }}
  </style>
</head>
<body>
  <div id="nav-placeholder"></div>

  <main class="content">
    <div class="daily-container">
      <div class="page-header">
        <h1>🌿 蕨積每日文章</h1>
        <p>植物・永續・碳盤查・生活 — 每天一篇，與你一起成長</p>
      </div>

      <div class="two-columns">
        <div class="main-col">
          <!-- 最新文章完整顯示 -->
          <div class="latest-article">
            <div class="latest-category">📌 {latest['category']}</div>
            <h1 class="latest-title">{latest['title']}</h1>
            <div class="latest-date">📅 {latest['date']}</div>
            <div class="latest-content">
              {latest['content']}
            </div>
            <a href="{latest['filename']}" class="read-more">🔗 查看獨立頁面 →</a>
          </div>

          <div class="section-title">📖 過往文章</div>
          <ul class="past-list">
"""
    
    for article in past_articles[:20]:
        cat_color = CATEGORY_COLORS.get(article["category"], "#6c757d")
        index_content += f"""
            <li class="past-item">
              <span class="past-badge" style="background: {cat_color};">{article['category']}</span>
              <a class="past-link" href="{article['filename']}">{article['title']}</a>
              <div class="past-meta">📅 {article['date']}</div>
            </li>"""
    
    index_content += """
          </ul>
        </div>

        <div class="sidebar-col">
          <div class="section-title">📚 歷史歸檔</div>
"""
    
    sorted_months = sorted(archive_by_month.keys(), reverse=True)
    for month in sorted_months:
        month_display = f"{month[:4]}年{int(month[5:7])}月"
        index_content += f"""
          <div class="archive-month">
            <div class="archive-month-title">{month_display}</div>
            <ul class="archive-list">"""
        for article in archive_by_month[month][:8]:
            index_content += f'<li><a href="{article["filename"]}">{article["title"][:25]}{"..." if len(article["title"]) > 25 else ""}</a></li>'
        if len(archive_by_month[month]) > 8:
            index_content += f'<li><a href="#" style="color:#aaa;">... 共{len(archive_by_month[month])}篇</a></li>'
        index_content += """
            </ul>
          </div>"""
    
    index_content += """
        </div>
      </div>
    </div>
  </main>

  <footer>
    <ul class="footer-links">
      <li><a href="shop.html">植物選品</a></li>
      <li><a href="consult.html">綠色顧問</a></li>
      <li><a href="fbnote.html">蕨望筆記</a></li>
      <li><a href="about.html">關於蕨積</a></li>
    </ul>
    <p class="footer-copy">© 2026 蕨積 FernBrom . All rights reserved.</p>
  </footer>

  <script>
    document.addEventListener('DOMContentLoaded', function () {{
      fetch('nav.html')
        .then(response => response.text())
        .then(data => {{
          document.getElementById('nav-placeholder').innerHTML = data;
          initNav();
        }})
        .catch(err => {{
          console.error('無法載入導覽列:', err);
          document.getElementById('nav-placeholder').innerHTML = 
            '<nav style="background:var(--moss);color:white;padding:0 4vw;height:72px;display:flex;align-items:center;">' +
            '<span style="font-family:Noto Serif TC,serif;font-weight:900;">🌿 蕨積</span>' +
            '</nav>';
        }});

      function initNav() {{
        var btn = document.getElementById('hamburger');
        var menu = document.getElementById('mobileMenu');
        if (btn && menu) {{
          btn.addEventListener('click', function () {{
            btn.classList.toggle('open');
            menu.classList.toggle('open');
          }});
          menu.querySelectorAll('.mobile-link').forEach(function (a) {{
            a.addEventListener('click', function () {{
              btn.classList.remove('open');
              menu.classList.remove('open');
            }});
          }});
        }}
        if (menu) {{
          menu.querySelectorAll('.mobile-parent').forEach(function (parent) {{
            parent.addEventListener('click', function () {{
              var id = parent.getAttribute('data-target');
              var sub = document.getElementById(id);
              var caretId = 'caret-' + id.replace('sub-', '');
              var caret = document.getElementById(caretId);
              var opening = !sub.classList.contains('open');
              menu.querySelectorAll('.mobile-sub').forEach(function (s) {{ s.classList.remove('open'); }});
              menu.querySelectorAll('.mobile-caret').forEach(function (c) {{ c.classList.remove('open'); }});
              if (opening) {{
                sub.classList.add('open');
                if (caret) caret.classList.add('open');
              }}
            }});
          }});
        }}
        window.addEventListener('scroll', function () {{
          var nav = document.getElementById('mainNav');
          if (nav) nav.classList.toggle('scrolled', window.scrollY > 20);
        }});
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }}
    }});
  </script>
</body>
</html>"""
    
    index_path = os.path.join(daily_post_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    print("📑 已更新 daily-post/index.html (套用官網模板)")

# ==================== 推送到網站倉庫 ====================
def commit_and_push_to_website():
    """將文章推送到網站倉庫的 daily-post 目錄"""
    print("=" * 50)
    print("開始推送到網站倉庫...")
    
    username = os.getenv("GITHUB_USERNAME", "isa930323-jpg")
    token = os.getenv("GH_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")
    
    print(f"📌 用戶名: {username}")
    print(f"📌 倉庫名: {repo_name}")
    print(f"📌 Token 是否存在: {'是' if token else '否'}")
    
    if not token:
        print("❌ 錯誤：GH_TOKEN 環境變數未設定")
        return
    
    website_repo = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    print(f"🔗 目標倉庫: https://github.com/{username}/{repo_name}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 臨時目錄: {tmpdir}")
        
        print("📥 正在 clone 網站倉庫...")
        clone_result = subprocess.run(
            ["git", "clone", website_repo, "website"],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        if clone_result.returncode != 0:
            print(f"❌ Clone 失敗: {clone_result.stderr}")
            return
        
        print("✅ Clone 成功")
        website_dir = os.path.join(tmpdir, "website")
        
        daily_post_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_post_dir, exist_ok=True)
        print(f"📁 daily-post 目錄: {daily_post_dir}")
        
        # 複製新文章
        article_copied = False
        if os.path.exists("articles"):
            for file in os.listdir("articles"):
                if file.endswith(".html"):
                    src = os.path.join("articles", file)
                    dst = os.path.join(daily_post_dir, file)
                    shutil.copy2(src, dst)
                    print(f"📄 複製文章: {file}")
                    article_copied = True
        
        if not article_copied:
            print("⚠️ 沒有找到文章檔案")
            return
        
        # 複製圖片（如果有）
        images_dir = os.path.join(daily_post_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        if os.path.exists("images"):
            for file in os.listdir("images"):
                src = os.path.join("images", file)
                dst = os.path.join(images_dir, file)
                shutil.copy2(src, dst)
                print(f"🖼️ 複製圖片: {file}")
        
        # 產生索引頁面（套用官網模板）
        generate_daily_post_index(daily_post_dir)
        
        # 提交並推送
        print("📤 提交並推送到 GitHub...")
        subprocess.run(["git", "config", "user.name", "jueji-bot"], cwd=website_dir, check=False)
        subprocess.run(["git", "config", "user.email", "bot@jueji.com"], cwd=website_dir, check=False)
        subprocess.run(["git", "add", "daily-post/"], cwd=website_dir, check=True)
        
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=website_dir,
            capture_output=True,
            text=True
        )
        
        if status.stdout.strip():
            commit_msg = f"每日發文 {datetime.now().strftime('%Y-%m-%d')}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=website_dir, check=False)
            push_result = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=website_dir,
                capture_output=True,
                text=True
            )
            
            if push_result.returncode == 0:
                print("✅ 成功推送到網站倉庫")
            else:
                print(f"❌ 推送失敗: {push_result.stderr}")
        else:
            print("📭 沒有新的變更需要推送")

# ==================== 主程式 ====================
def main():
    print("=" * 50)
    print("🌿 蕨積每日發文機器人啟動")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    title, content, category = generate_article()
    if not title or not content:
        print("❌ 文章生成失敗，結束程式")
        sys.exit(1)
    
    save_article_as_html(title, content, category)
    commit_and_push_to_website()
    
    print("🎉 每日發文流程完成")

if __name__ == "__main__":
    main()
