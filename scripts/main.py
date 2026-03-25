#!/usr/bin/env python3
"""
每日自動發文機器人
- 使用 DeepSeek API 生成文章
- 將文章保存為 HTML
- 推送到網站倉庫的 daily-post 目錄
"""

import os
import sys
import json
import subprocess
import shutil
import tempfile
from datetime import datetime
import requests

# ==================== 配置 ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 文章生成提示詞
PROMPT_TEMPLATE = """請寫一篇關於「蕨類植物」的科普文章，主題可以圍繞：
- 蕨類植物的生態特徵
- 蕨類的繁殖方式
- 常見蕨類品種介紹
- 蕨類在園藝中的應用

要求：
1. 標題要吸引人
2. 內容約 500-800 字
3. 語言使用繁體中文
4. 結尾加上「🌿 蕨積 - 讓生活多一點綠」"""

# ==================== 文章生成 ====================
def generate_article():
    """调用 DeepSeek API 生成文章内容"""
    if not DEEPSEEK_API_KEY:
        print("❌ 錯誤：DEEPSEEK_API_KEY 環境變數未設定")
        return None, None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一位植物學科普作家，擅長撰寫有趣且專業的植物文章。"},
            {"role": "user", "content": PROMPT_TEMPLATE}
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
        
        # 提取標題（假設第一行是標題）
        lines = content.strip().split("\n")
        title = lines[0].replace("#", "").strip()
        if not title:
            title = f"蕨類植物日誌 {datetime.now().strftime('%Y-%m-%d')}"
        
        print(f"✅ 文章生成成功：{title}")
        return title, content
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None, None

def save_article_as_html(title, content, output_dir="articles"):
    """將文章儲存為 HTML 檔案"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 檔案名稱：日期-標題簡化版
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = title.replace(" ", "-").replace("/", "-")[:30]
    filename = f"{date_str}-{safe_title}.html"
    filepath = os.path.join(output_dir, filename)
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 蕨積每日文章</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            background: #faf8f4;
            color: #2c3e2f;
        }}
        h1 {{ color: #2c5e2e; border-left: 4px solid #6b8c5c; padding-left: 1rem; }}
        .date {{ color: #7f8c6d; margin-bottom: 2rem; }}
        hr {{ margin: 2rem 0; border: none; border-top: 1px solid #e0d6cc; }}
        .footer {{ text-align: center; margin-top: 3rem; color: #7f8c6d; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="date">📅 {datetime.now().strftime("%Y年%m月%d日")}</div>
    <div class="content">
        {content.replace("\n", "<br>")}
    </div>
    <hr>
    <div class="footer">
        🌿 蕨積 - 讓生活多一點綠<br>
        每日一篇，與蕨類一起呼吸
    </div>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"📄 文章已儲存：{filepath}")
    return filepath

# ==================== 推送到網站倉庫 ====================
def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面"""
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html":
            articles.append(file)
    
    articles.sort(reverse=True)  # 最新的在前
    
    if not articles:
        return
    
    index_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蕨積每日文章</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #2c3e2f;
            background-color: #faf8f4;
            padding: 2rem;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #2c5e2e; margin-bottom: 2rem; font-size: 2rem; }}
        .article-list {{ list-style: none; padding: 0; }}
        .article-item {{
            margin: 1rem 0;
            padding: 1.2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .article-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .article-link {{
            font-size: 1.2rem;
            font-weight: 500;
            color: #4a7c59;
            text-decoration: none;
        }}
        .article-link:hover {{ text-decoration: underline; }}
        .article-date {{
            color: #7f8c6d;
            font-size: 0.85rem;
            margin-top: 0.5rem;
        }}
        .back-link {{
            display: inline-block;
            margin-top: 2rem;
            color: #4a7c59;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 蕨積每日文章</h1>
        <ul class="article-list">
            {''.join([f'<li class="article-item"><a class="article-link" href="{article}">{article.replace(".html", "").replace("-", " / ")}</a><div class="article-date">📅 {article.replace(".html", "").split("-")[-1] if "-" in article else "最新"}</div></li>' for article in articles])}
        </ul>
        <a href="/" class="back-link">← 返回首頁</a>
    </div>
</body>
</html>"""
    
    index_path = os.path.join(daily_post_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    print("📑 已更新 daily-post/index.html")

def commit_and_push_to_website():
    """將文章推送到網站倉庫的 daily-post 目錄"""
    print("=" * 50)
    print("開始推送到網站倉庫...")
    
    username = os.getenv("GITHUB_USERNAME", "fangyung0323")
    token = os.getenv("GH_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")
    
    print(f"📌 用戶名: {username}")
    print(f"📌 倉庫名: {repo_name}")
    print(f"📌 Token 是否存在: {'是' if token else '否'}")
    
    if not token:
        print("❌ 錯誤：GH_TOKEN 環境變數未設定")
        return
    
    # 使用包含 Token 的 URL
    website_repo = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    print(f"🔗 目標倉庫: https://github.com/{username}/{repo_name}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 臨時目錄: {tmpdir}")
        
        # 1. Clone 網站倉庫
        print("📥 正在 clone 網站倉庫...")
        clone_result = subprocess.run(
            ["git", "clone", website_repo, "website"],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        if clone_result.returncode != 0:
            print(f"❌ Clone 失敗: {clone_result.stderr}")
            print("請檢查：")
            print("  1. GH_TOKEN 是否正確")
            print("  2. Token 是否有 repo 權限")
            print("  3. 倉庫名稱是否正確")
            return
        
        print("✅ Clone 成功")
        website_dir = os.path.join(tmpdir, "website")
        
        # 2. 確保 daily-post 目錄存在
        daily_post_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_post_dir, exist_ok=True)
        print(f"📁 daily-post 目錄: {daily_post_dir}")
        
        # 3. 複製新產生的文章
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
            print("⚠️ 沒有找到文章檔案，請檢查文章生成步驟")
            return
        
        # 4. 複製圖片（如果有）
        images_dir = os.path.join(daily_post_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        if os.path.exists("images"):
            for file in os.listdir("images"):
                src = os.path.join("images", file)
                dst = os.path.join(images_dir, file)
                shutil.copy2(src, dst)
                print(f"🖼️ 複製圖片: {file}")
        
        # 5. 產生索引頁面
        generate_daily_post_index(daily_post_dir)
        
        # 6. 提交並推送
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
    print("🌿 蕨積每日發文機器人啟動")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 生成文章
    title, content = generate_article()
    if not title or not content:
        print("❌ 文章生成失敗，結束程式")
        sys.exit(1)
    
    # 2. 儲存文章
    save_article_as_html(title, content)
    
    # 3. 推送到網站倉庫
    commit_and_push_to_website()
    
    print("🎉 每日發文流程完成")

if __name__ == "__main__":
    main()
