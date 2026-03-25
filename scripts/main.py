def commit_and_push_to_website():
    """將文章推送到網站倉庫的 daily-post 目錄"""
    
    # 從環境變數取得網站倉庫資訊
    username = os.getenv("GITHUB_USERNAME", "fangyung0323")
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")
    
    # 檢查必要環境變數
    if not token:
        print("❌ 錯誤：GITHUB_TOKEN 環境變數未設定")
        print("請在 Render Dashboard 設定 GITHUB_TOKEN")
        return
    
    # 使用包含 Token 的 URL（關鍵修正！）
    website_repo = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    print(f"🔗 目標倉庫: https://github.com/{username}/{repo_name}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 臨時目錄: {tmpdir}")
        
        # 1. Clone 網站倉庫（使用包含 Token 的 URL）
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
            print("  1. GITHUB_TOKEN 是否正確")
            print("  2. Token 是否有 repo 權限")
            print("  3. 倉庫名稱是否正確")
            return
        
        print("✅ Clone 成功")
        website_dir = os.path.join(tmpdir, "website")
        
        # 2. 確保 daily-post 目錄存在
        daily_post_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_post_dir, exist_ok=True)
        print(f"📁 daily-post 目錄: {daily_post_dir}")
        
        # 3. 複製新產生的文章（放入 daily-post 目錄）
        article_copied = False
        if os.path.exists("articles"):
            for file in os.listdir("articles"):
                if file.endswith(".html"):
                    src = os.path.join("articles", file)
                    dst = os.path.join(daily_post_dir, file)
                    shutil.copy2(src, dst)
                    print(f"📄 複製文章: {file}")
                    article_copied = True
        
        # 4. 複製圖片（放入 daily-post/images 目錄）
        images_dir = os.path.join(daily_post_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        if os.path.exists("images"):
            for file in os.listdir("images"):
                src = os.path.join("images", file)
                dst = os.path.join(images_dir, file)
                shutil.copy2(src, dst)
                print(f"🖼️ 複製圖片: {file}")
        
        if not article_copied:
            print("⚠️ 沒有找到文章檔案，請檢查文章生成步驟")
            return
        
        # 5. 產生 daily-post 目錄的索引頁面
        generate_daily_post_index(daily_post_dir)
        
        # 6. 提交並推送
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
            push_result = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=website_dir,
                capture_output=True,
                text=True
            )
            
            if push_result.returncode == 0:
                print("✅ 成功推送到網站倉庫")
                print(f"🔗 文章網址: https://www.fernbrom.com/daily-post/{file if article_copied else ''}")
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
    
    articles.sort(reverse=True)  # 最新的在前
    
    # 如果沒有文章，不產生 index
    if not articles:
        return
    
    index_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蕨積每日文章</title>
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
            padding: 2rem;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c5e2e;
            margin-bottom: 2rem;
            font-size: 2rem;
        }}
        .article-list {{
            list-style: none;
            padding: 0;
        }}
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
        .article-link:hover {{
            text-decoration: underline;
        }}
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
