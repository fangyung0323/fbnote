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
    
    # 讀取 API 金鑰
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_key:
        print("❌ 錯誤：請設定 DEEPSEEK_API_KEY 環境變數")
        sys.exit(1)
    
    # 選擇今日類別
    today_category = get_today_category()
    category_info = CATEGORIES[today_category]
    print(f"📝 今日類別：{category_info['name']}")
    
    # 1. 生成文章
    article_gen = ArticleGenerator(deepseek_key)
    article = article_gen.generate(today_category, category_info)
    
    # 2. 生成圖片
    image_gen = ImageGenerator(deepseek_key)
    image_path = image_gen.generate(category_info["image_prompt"], today_category)
    
    # 3. 產生 HTML 檔案（儲存到本地的 articles/ 目錄）
    html_path = generate_html(article, image_path)
    print(f"✅ 文章已生成：{html_path}")
    
    # 4. 推送到網站倉庫
    commit_and_push_to_website()
    
    print("🎉 執行完畢！")

def generate_html(article, image_path):
    """產生完整的 HTML 文章頁面"""
    
    # 確保目錄存在
    os.makedirs("articles", exist_ok=True)
    
    # 產生檔名：類別-日期.html
    slug = f"{article['category_key']}-{datetime.now().strftime('%Y%m%d')}"
    html_path = f"articles/{slug}.html"
    
    # 完整的 HTML 頁面（包含三個底部連結）
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{article.get('summary', '')}">
    <title>{article['title']} - 蕨積</title>
    
    <!-- Open Graph 標籤 -->
    <meta property="og:title" content="{article['title']}">
    <meta property="og:description" content="{article.get('summary', '')}">
    <meta property="og:image" content="{image_path}">
    <meta property="og:type" content="article">
    
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #2c3e2f;
            background-color: #faf8f4;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .article-header {{
            margin-bottom: 2rem;
            text-align: center;
        }}
        
        .category-badge {{
            display: inline-block;
            background: #4a7c59;
            color: white;
            padding: 0.3rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        
        h1 {{
            font-size: 2rem;
            color: #2c5e2e;
            margin-bottom: 1rem;
        }}
        
        .article-meta {{
            color: #7f8c6d;
            font-size: 0.9rem;
            margin-bottom: 2rem;
        }}
        
        .featured-image {{
            width: 100%;
            border-radius: 12px;
            margin: 2rem 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .article-content {{
            font-size: 1.1rem;
        }}
        
        .article-content h2 {{
            color: #3d6b3e;
            margin: 2rem 0 1rem 0;
            font-size: 1.6rem;
        }}
        
        .article-content h3 {{
            color: #4a7c59;
            margin: 1.5rem 0 0.8rem 0;
            font-size: 1.3rem;
        }}
        
        .article-content p {{
            margin-bottom: 1.2rem;
        }}
        
        .article-content ul, .article-content ol {{
            margin: 1rem 0 1rem 2rem;
        }}
        
        .article-content li {{
            margin-bottom: 0.5rem;
        }}
        
        .article-footer {{
            margin: 2rem 0 1rem 0;
            padding-top: 1rem;
            border-top: 1px solid #e0dbd0;
            text-align: center;
            color: #7f8c6d;
            font-size: 0.9rem;
        }}
        
        .tags {{
            margin: 1rem 0;
            text-align: center;
        }}
        
        .tag {{
            display: inline-block;
            background: #e8e5dd;
            color: #4a7c59;
            padding: 0.2rem 0.8rem;
            border-radius: 15px;
            font-size: 0.8rem;
            margin-right: 0.5rem;
        }}
        
        .reading-time {{
            background: #e8f0e6;
            padding: 0.2rem 0.8rem;
            border-radius: 15px;
            font-size: 0.8rem;
            display: inline-block;
        }}
        
        /* 底部導航連結樣式 */
        .bottom-nav {{
            text-align: center;
            margin: 2rem 0 1rem 0;
            padding: 1rem 0;
            border-top: 1px solid #e0dbd0;
        }}
        
        .bottom-nav a {{
            color: #4a7c59;
            text-decoration: none;
            margin: 0 0.75rem;
            font-size: 0.95rem;
            transition: color 0.2s;
        }}
        
        .bottom-nav a:hover {{
            color: #2c5e2e;
            text-decoration: underline;
        }}
        
        .nav-separator {{
            color: #ccc;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            h1 {{
                font-size: 1.6rem;
            }}
            .bottom-nav a {{
                margin: 0 0.4rem;
                font-size: 0.85rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <article>
            <div class="article-header">
                <div class="category-badge">{article['category']} {get_category_emoji(article['category_key'])}</div>
                <h1>{article['title']}</h1>
                <div class="article-meta">
                    📅 {article.get('date', datetime.now().strftime('%Y年%m月%d日'))} | 
                    <span class="reading-time">📖 {article.get('reading_time', 3)} 分鐘閱讀</span>
                </div>
            </div>
            
            <img src="{image_path}" alt="{article['title']}" class="featured-image">
            
            <div class="article-content">
                {article.get('content', '')}
            </div>
            
            <div class="tags">
                🔖 {''.join([f'<span class="tag">#{tag}</span>' for tag in article.get('tags', [])])}
            </div>
            
            <div class="article-footer">
                🌿 蕨積 - 讓生活多一點綠<br>
                每日一篇，與你一起成長
            </div>
            
            <!-- 底部三個導航連結 -->
            <div class="bottom-nav">
                <a href="index.html">← 返回文章列表</a>
                <span class="nav-separator">|</span>
                <a href="./shop.html">🌱 植物選品</a>
                <span class="nav-separator">|</span>
                <a href="./consulting.html">💚 綠色顧問</a>
            </div>
        </article>
    </div>
</body>
</html>"""
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return html_path

def get_category_emoji(category_key):
    """根據類別回傳對應的 emoji"""
    emojis = {
        "plant": "🌱",
        "carbon": "🌍",
        "sustainability": "♻️",
        "life": "✨"
    }
    return emojis.get(category_key, "📝")

def commit_and_push_to_website():
    """將文章推送到網站倉庫的 daily-post 目錄"""
    
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
        
        article_copied = False
        if os.path.exists("articles"):
            for file in os.listdir("articles"):
                if file.endswith(".html"):
                    src = os.path.join("articles", file)
                    dst = os.path.join(daily_post_dir, file)
                    shutil.copy2(src, dst)
                    print(f"📄 複製文章: {file}")
                    article_copied = True
        
        images_dir = os.path.join(daily_post_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        if os.path.exists("images"):
            for file in os.listdir("images"):
                src = os.path.join("images", file)
                dst = os.path.join(images_dir, file)
                shutil.copy2(src, dst)
                print(f"🖼️ 複製圖片: {file}")
        
        if not article_copied:
            print("⚠️ 沒有找到文章檔案")
            return
        
        generate_daily_post_index(daily_post_dir)
        
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

def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面"""
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html":
            articles.append(file)
    
    articles.sort(reverse=True)
    
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
            transition: transform 0.2s;
        }}
        .article-item:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .article-link {{ font-size: 1.2rem; font-weight: 500; color: #4a7c59; text-decoration: none; }}
        .article-link:hover {{ text-decoration: underline; }}
        .article-date {{ color: #7f8c6d; font-size: 0.85rem; margin-top: 0.5rem; }}
        .bottom-nav {{
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #e0dbd0;
        }}
        .bottom-nav a {{ color: #4a7c59; text-decoration: none; margin: 0 0.5rem; }}
        .bottom-nav a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 蕨積每日文章</h1>
        <ul class="article-list">
            {''.join([f'<li class="article-item"><a class="article-link" href="{article}">{article.replace(".html", "").replace("-", " / ")}</a><div class="article-date">📅 {article.replace(".html", "").split("-")[-1] if "-" in article else "最新"}</div></li>' for article in articles])}
        </ul>
        <div class="bottom-nav">
            <a href="./shop.html">🌱 植物選品</a>
            <span>|</span>
            <a href="./consulting.html">💚 綠色顧問</a>
        </div>
    </div>
</body>
</html>"""
    
    with open(os.path.join(daily_post_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_content)
    print("📑 已更新 daily-post/index.html")

if __name__ == "__main__":
    main()
