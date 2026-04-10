#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import shutil
import re
from datetime import datetime
from categories import CATEGORIES, get_today_category
from article_generator import ArticleGenerator
from image_generator import ImageGenerator

def main():
    print(f"🤖 蕨積機器人啟動 - {datetime.now()}")
    
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("❌ 錯誤：請設定 DEEPSEEK_API_KEY 環境變數")
        sys.exit(1)
    
    today_category = get_today_category()
    category_info = CATEGORIES[today_category]
    print(f"📝 今日類別：{category_info['name']}")
    
    article_gen = ArticleGenerator(deepseek_key)
    article = article_gen.generate(today_category, category_info)
    
    image_gen = ImageGenerator(deepseek_key)
    image_path = image_gen.generate(category_info["image_prompt"], today_category)
    
    html_path = generate_html(article, image_path)
    print(f"✅ 文章已生成：{html_path}")
    
    commit_and_push_to_website()
    
    print("🎉 執行完畢！")

def generate_html(article, image_path):
    os.makedirs("articles", exist_ok=True)
    slug = f"{article['category_key']}-{datetime.now().strftime('%Y%m%d')}"
    html_path = f"articles/{slug}.html"
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article['title']} - 蕨積</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #2c3e2f;
            background-color: #faf8f4;
            padding: 2rem;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #2c5e2e; margin-bottom: 1rem; }}
        .meta {{ color: #7f8c6d; margin: 1rem 0; }}
        img {{ max-width: 100%; border-radius: 12px; margin: 1rem 0; }}
        .footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; text-align: center; }}
        .nav-links {{ text-align: center; margin-top: 1rem; }}
        .nav-links a {{ color: #4a7c59; margin: 0 0.5rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{article['title']}</h1>
        <div class="meta">📂 {article['category']} | 📅 {article.get('date', datetime.now().strftime('%Y年%m月%d日'))}</div>
        <img src="{image_path}" alt="{article['title']}">
        <div class="content">{article.get('content', '')}</div>
        <div class="footer">
            🌿 蕨積 - 讓生活多一點綠
            <div class="nav-links">
                <a href="index.html">← 返回文章列表</a>
                <a href="../shop.html">植物選品</a>
                <a href="../consult.html">綠色顧問</a>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return html_path

def commit_and_push_to_website():
    username = os.getenv("GITHUB_USERNAME", "fangyung0323")
    token = os.getenv("GH_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")
    
    if not token:
        print("❌ 錯誤：GH_TOKEN 環境變數未設定")
        return
    
    website_repo = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    print(f"🔗 目標倉庫: https://github.com/{username}/{repo_name}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 臨時目錄: {tmpdir}")
        
        clone_result = subprocess.run(
            ["git", "clone", "--depth", "1", website_repo, "website"],
            cwd=tmpdir, capture_output=True, text=True
        )
        
        if clone_result.returncode != 0:
            print(f"❌ Clone 失敗: {clone_result.stderr}")
            return
        
        print("✅ Clone 成功")
        website_dir = os.path.join(tmpdir, "website")
        daily_post_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_post_dir, exist_ok=True)
        
        if os.path.exists("articles"):
            for file in os.listdir("articles"):
                if file.endswith(".html"):
                    shutil.copy2(os.path.join("articles", file), os.path.join(daily_post_dir, file))
                    print(f"📄 複製文章: {file}")
        
        images_dir = os.path.join(daily_post_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        if os.path.exists("images"):
            for file in os.listdir("images"):
                shutil.copy2(os.path.join("images", file), os.path.join(images_dir, file))
                print(f"🖼️ 複製圖片: {file}")
        
        generate_index(daily_post_dir)
        
        subprocess.run(["git", "config", "user.name", "jueji-bot"], cwd=website_dir, check=False)
        subprocess.run(["git", "config", "user.email", "bot@jueji.com"], cwd=website_dir, check=False)
        subprocess.run(["git", "add", "daily-post/"], cwd=website_dir, check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], cwd=website_dir, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"每日發文 {datetime.now().strftime('%Y-%m-%d')}"], cwd=website_dir, check=False)
            push_result = subprocess.run(["git", "push", "origin", "main"], cwd=website_dir, capture_output=True, text=True)
            if push_result.returncode == 0:
                print("✅ 成功推送到網站倉庫")
            else:
                print(f"❌ 推送失敗: {push_result.stderr}")
        else:
            print("📭 沒有新的變更需要推送")

def generate_index(daily_post_dir):
    """產生單純的文章列表頁面（無搜尋功能，穩定版本）"""
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html":
            articles.append(file)
    articles.sort(reverse=True)
    
    index_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蕨積每日文章</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #2c3e2f;
            background-color: #faf8f4;
            padding: 2rem;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #2c5e2e; margin-bottom: 2rem; text-align: center; }}
        .article-list {{ list-style: none; padding: 0; }}
        .article-item {{
            margin: 1rem 0;
            padding: 1rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .article-link {{
            font-size: 1.1rem;
            color: #4a7c59;
            text-decoration: none;
        }}
        .article-link:hover {{ text-decoration: underline; }}
        .bottom-nav {{
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #ddd;
        }}
        .bottom-nav a {{ color: #4a7c59; margin: 0 0.5rem; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 蕨積每日文章</h1>
        <ul class="article-list">
            {''.join([f'<li class="article-item"><a class="article-link" href="{article}">{article.replace(".html", "")}</a></li>' for article in articles])}
        </ul>
        <div class="bottom-nav">
            <a href="../shop.html">植物選品</a> | <a href="../consult.html">綠色顧問</a>
        </div>
    </div>
</body>
</html>"""
    
    with open(os.path.join(daily_post_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_content)
    print("📑 已更新 daily-post/index.html")

if __name__ == "__main__":
    main()
