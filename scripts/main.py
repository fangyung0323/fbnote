#!/usr/bin/env python3
"""
每日自動發文機器人
- 使用 DeepSeek API 生成文章（四大類別輪換：植物、永續、碳盤查、生活）
- 將文章保存為 HTML
- 推送到網站倉庫的 daily-post 目錄
- 自動生成簡潔的索引頁面
"""

import os
import sys
import subprocess
import shutil
import tempfile
import re
from datetime import datetime
import requests

# ==================== 配置 ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

CATEGORIES = ["植物", "永續", "碳盤查", "生活"]
CATEGORY_COLORS = {
    "植物": "#4a7c59",
    "永續": "#2c7a4d",
    "碳盤查": "#1e6f5c",
    "生活": "#b88b4a"
}

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
    if not DEEPSEEK_API_KEY:
        print("❌ 錯誤：DEEPSEEK_API_KEY 環境變數未設定")
        return None, None, None
    category = get_today_category()
    prompt = PROMPT_TEMPLATES[category]
    print(f"📌 今日主題類別：{category}")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "system", "content": SYSTEM_PROMPTS[category]}, {"role": "user", "content": prompt}],
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
        return title, content, category
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None, None, None

def save_article_as_html(title, content, category, output_dir="articles"):
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = title.replace(" ", "-").replace("/", "-").replace("?", "").replace("！", "")[:50]
    filename = f"{date_str}-{safe_title}.html"
    filepath = os.path.join(output_dir, filename)
    category_color = CATEGORY_COLORS.get(category, "#4a7c59")
    content_html = content.replace("\n", "<br>")
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 蕨積每日文章</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
    <div class="content">{content_html}</div>
    <hr>
    <div class="footer">🌿 蕨積 - 讓生活多一點綠<br>每日一篇，與你一起成長</div>
    <a href="index.html" class="back-link">← 返回文章列表</a>
</body>
</html>"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"📄 文章已儲存：{filepath}")
    return filepath

# ==================== 索引頁面生成（簡潔版） ====================
def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面（簡潔版）"""
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html" and len(file) >= 10 and file[4] == '-' and file[7] == '-':
            filepath = os.path.join(daily_post_dir, file)
            category = "未分類"
            title = ""
            date_str = file[:10]
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    full_content = f.read()
                    match_cat = re.search(r'<div class="category-tag">📌 (.+?)</div>', full_content)
                    if match_cat:
                        category = match_cat.group(1)
                    match_title = re.search(r'<h1>(.+?)</h1>', full_content)
                    if match_title:
                        title = match_title.group(1)
            except:
                title = file.replace(".html", "").replace(date_str + "-", "").replace("-", " / ")
            articles.append({
                "filename": file,
                "date": date_str,
                "title": title,
                "category": category
            })
    articles.sort(key=lambda x: x["date"], reverse=True)
    if not articles:
        index_content = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>蕨積每日文章</title><style>body{font-family:sans-serif;max-width:800px;margin:0 auto;padding:2rem;background:#faf8f4;}</style></head><body><h1>🌿 蕨積每日文章</h1><p>📭 目前還沒有文章，等待機器人發文中...</p></body></html>"""
        with open(os.path.join(daily_post_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_content)
        print("📑 已更新 daily-post/index.html (無文章)")
        return
    index_content = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蕨積每日文章</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2rem; background: #faf8f4; color: #2c3e2f; }
        h1 { color: #2c5e2e; border-left: 4px solid #6b8c5c; padding-left: 1rem; }
        .subtitle { color: #7f8c6d; margin-bottom: 1.5rem; }
        .article-list { list-style: none; padding: 0; }
        .article-item { margin: 1rem 0; padding: 1rem; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .article-link { font-size: 1.1rem; font-weight: 500; color: #4a7c59; text-decoration: none; display: block; }
        .article-link:hover { text-decoration: underline; }
        .article-date { color: #7f8c6d; font-size: 0.8rem; margin-top: 0.3rem; }
        .category-badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 12px; font-size: 0.7rem; color: white; margin-right: 0.5rem; }
        .footer { text-align: center; margin-top: 2rem; color: #7f8c6d; font-size: 0.8rem; }
    </style>
</head>
<body>
    <h1>🌿 蕨積每日文章</h1>
    <div class="subtitle">植物・永續・碳盤查・生活 — 每天一篇，與你一起成長</div>
    <ul class="article-list">
"""
    for article in articles[:30]:
        cat_color = CATEGORY_COLORS.get(article["category"], "#6c757d")
        index_content += f"""
        <li class="article-item">
            <span class="category-badge" style="background: {cat_color};">{article['category']}</span>
            <a class="article-link" href="{article['filename']}">{article['title']}</a>
            <div class="article-date">📅 {article['date']}</div>
        </li>"""
    index_content += """
    </ul>
    <div class="footer">🌿 蕨積 - 讓生活多一點綠<br>每日一篇，與你一起成長</div>
</body>
</html>"""
    with open(os.path.join(daily_post_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_content)
    print(f"📑 已更新 daily-post/index.html (共 {len(articles)} 篇文章)")

# ==================== 推送 ====================
def commit_and_push_to_website():
    print("=" * 50)
    print("開始推送到網站倉庫...")
    username = os.getenv("GITHUB_USERNAME", "isa930323-jpg")
    token = os.getenv("GH_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")
    print(f"📌 用戶名: {username}")
    print(f"📌 倉庫名: {repo_name}")
    if not token:
        print("❌ 錯誤：GH_TOKEN 環境變數未設定")
        return
    repo_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    with tempfile.TemporaryDirectory() as tmpdir:
        print("📥 正在 clone 網站倉庫...")
        r = subprocess.run(["git", "clone", repo_url, "website"], cwd=tmpdir, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"❌ Clone 失敗: {r.stderr}")
            return
        website_dir = os.path.join(tmpdir, "website")
        daily_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_dir, exist_ok=True)
        if os.path.exists("articles"):
            for f in os.listdir("articles"):
                if f.endswith(".html"):
                    shutil.copy2(os.path.join("articles", f), os.path.join(daily_dir, f))
        generate_daily_post_index(daily_dir)
        subprocess.run(["git", "config", "user.name", "jueji-bot"], cwd=website_dir, check=False)
        subprocess.run(["git", "config", "user.email", "bot@jueji.com"], cwd=website_dir, check=False)
        subprocess.run(["git", "add", "daily-post/"], cwd=website_dir, check=True)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=website_dir, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"每日發文 {datetime.now().strftime('%Y-%m-%d')}"], cwd=website_dir, check=False)
            push = subprocess.run(["git", "push", "origin", "main"], cwd=website_dir, capture_output=True, text=True)
            if push.returncode == 0:
                print("✅ 成功推送到網站倉庫")
            else:
                print(f"❌ 推送失敗: {push.stderr}")
        else:
            print("📭 沒有新的變更需要推送")

def main():
    print("=" * 50)
    print("🌿 蕨積每日發文機器人啟動")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    title, content, cat = generate_article()
    if not title:
        sys.exit(1)
    save_article_as_html(title, content, cat)
    commit_and_push_to_website()
    print("🎉 每日發文流程完成")

if __name__ == "__main__":
    main()
