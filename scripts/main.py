import os
import sys
import subprocess
import tempfile
import shutil
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
    
    # 4. 推送到網站倉庫的 /daily-post/ 目錄
    commit_and_push_to_website()
    
    print("🎉 執行完畢！")

def generate_html(article, image_path):
    """產生 HTML 文章檔案"""
    # 確保本地目錄存在
    os.makedirs("articles", exist_ok=True)
    
    # 產生檔名：類別-日期.html，例如 plant-20250325.html
    slug = f"{article['category_key']}-{datetime.now().strftime('%Y%m%d')}"
    html_path = f"articles/{slug}.html"
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{article['title']} - 蕨積</title>
    <meta name="description" content="{article.get('summary', '')}">
    <style>
        /* 可加入你的網站樣式 */
        body {{
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #2c3e2f;
            background: #faf8f4;
        }}
        h1 {{ color: #2c5e2e; }}
        .meta {{ color: #7f8c6d; font-size: 0.9rem; margin: 1rem 0; }}
        img {{ max-width: 100%; border-radius: 12px; margin: 1rem 0; }}
        .tags {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; }}
        .tag {{ display: inline-block; background: #e8e5dd; padding: 0.2rem 0.8rem; border-radius: 15px; font-size: 0.8rem; margin-right: 0.5rem; }}
    </style>
</head>
<body>
    <article>
        <h1>{article['title']}</h1>
        <div class="meta">
            📂 {article['category']} | 📅 {article.get('date', datetime.now().strftime('%Y年%m月%d日'))} | 📖 {article.get('reading_time', 3)} 分鐘閱讀
        </div>
        <img src="{image_path}" alt="{article['title']}">
        <div class="content">
            {article.get('content', '')}
        </div>
        <div class="tags">
            🔖 {''.join([f'<span class="tag">#{tag}</span>' for tag in article.get('tags', [])])}
        </div>
    </article>
</body>
</html>"""
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return html_path

def commit_and_push_to_website():
    """將文章推送到網站倉庫的 daily-post 目錄"""
    
    # 從環境變數取得網站倉庫資訊
    username = os.getenv("GITHUB_USERNAME", "fangyung0323")
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")  # 你的網站倉庫名稱
    
    if token:
        website_repo = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    else:
        website_repo = f"https://github.com/{username}/{repo_name}.git"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 臨時目錄: {tmpdir}")
        
        # 1. Clone 網站倉庫
        print("📥 正在 clone 網站倉庫...")
        clone_result = subprocess.run(
            ["git", "clone", "--depth", "1", website_repo, "website"],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        
        if clone_result.returncode != 0:
            print(f"❌ Clone 失敗: {clone_result.stderr}")
            return
        
        website_dir = os.path.join(tmpdir, "website")
        
        # 2. 確保 daily-post 目錄存在
        daily_post_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_post_dir, exist_ok=True)
        
        # 3. 複製新產生的文章（放入 daily-post 目錄）
        if os.path.exists("articles"):
            for file in os.listdir("articles"):
                if file.endswith(".html"):
                    src = os.path.join("articles", file)
                    dst = os.path.join(daily_post_dir, file)
                    shutil.copy2(src, dst)
                    print(f"📄 複製文章: {file}")
        
        # 4. 複製圖片（放入 daily-post/images 目錄）
        images_dir = os.path.join(daily_post_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        if os.path.exists("images"):
            for file in os.listdir("images"):
                src = os.path.join("images", file)
                dst = os.path.join(images_dir, file)
                shutil.copy2(src, dst)
                print(f"🖼️ 複製圖片: {file}")
        
        # 5. 提交並推送
        print("📤 提交並推送到 GitHub...")
        subprocess.run(["git", "config", "user.name", "jueji-bot"], cwd=website_dir, check=False)
        subprocess.run(["git", "config", "user.email", "bot@jueji.com"], cwd=website_dir, check=False)
        subprocess.run(["git", "add", "daily-post/"], cwd=website_dir, check=True)
        
        # 檢查是否有變更
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=website_dir,
            capture_output=True,
            text=True
        )
        
        if status.stdout.strip():
            commit_msg = f"每日發文 {datetime.now().strftime('%Y-%m-%d')}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=website_dir, check=False)
            push_result = subprocess.run(["git", "push"], cwd=website_dir, capture_output=True, text=True)
            
            if push_result.returncode == 0:
                print("✅ 成功推送到網站倉庫")
            else:
                print(f"❌ 推送失敗: {push_result.stderr}")
        else:
            print("📭 沒有新的變更需要推送")

if __name__ == "__main__":
    main()
