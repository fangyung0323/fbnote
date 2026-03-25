def commit_and_push():
    """將文章和圖片推送到網站倉庫"""
    
    # 從環境變數取得網站倉庫 URL
    website_repo = os.getenv("WEBSITE_REPO_URL")
    if not website_repo:
        # 如果沒有設定完整 URL，則組合
        username = os.getenv("GITHUB_USERNAME", "fangyung0323")
        token = os.getenv("GITHUB_TOKEN")
        repo_name = os.getenv("WEBSITE_REPO_NAME", "jueji-website")  # 你的網站倉庫名稱
        
        if token:
            website_repo = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
        else:
            website_repo = f"https://github.com/{username}/{repo_name}.git"
    
    # 方法：使用臨時目錄 clone 網站倉庫
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"📁 臨時目錄: {tmpdir}")
        
        # 1. Clone 網站倉庫
        clone_cmd = ["git", "clone", website_repo, "website"]
        subprocess.run(clone_cmd, cwd=tmpdir, check=True, capture_output=True)
        
        # 2. 複製新產生的文章和圖片
        website_dir = os.path.join(tmpdir, "website")
        
        # 複製 articles 目錄
        if os.path.exists("articles"):
            dest_articles = os.path.join(website_dir, "articles")
            if os.path.exists(dest_articles):
                shutil.rmtree(dest_articles)
            shutil.copytree("articles", dest_articles)
        
        # 複製 images 目錄
        if os.path.exists("images"):
            dest_images = os.path.join(website_dir, "images")
            if os.path.exists(dest_images):
                shutil.rmtree(dest_images)
            shutil.copytree("images", dest_images)
        
        # 3. 提交並推送
        subprocess.run(["git", "config", "user.name", "jueji-bot"], cwd=website_dir, check=False)
        subprocess.run(["git", "config", "user.email", "bot@jueji.com"], cwd=website_dir, check=False)
        subprocess.run(["git", "add", "."], cwd=website_dir, check=True)
        
        # 檢查是否有變更
        status = subprocess.run(["git", "status", "--porcelain"], cwd=website_dir, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"每日發文 {datetime.now().strftime('%Y-%m-%d')}"], cwd=website_dir, check=False)
            push_result = subprocess.run(["git", "push"], cwd=website_dir, capture_output=True, text=True)
            if push_result.returncode == 0:
                print("✅ 已推送到網站倉庫")
            else:
                print(f"❌ 推送失敗: {push_result.stderr}")
        else:
            print("📭 沒有新的變更需要推送")
