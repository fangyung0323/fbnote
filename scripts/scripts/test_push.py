import os
import subprocess
import tempfile

def test_push():
    username = os.getenv("GITHUB_USERNAME", "isa930323-jpg")
    token = os.getenv("GH_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")
    
    print(f"用户名: {username}")
    print(f"仓库: {repo_name}")
    print(f"Token存在: {'是' if token else '否'}")
    
    if not token:
        print("❌ Token 未设置")
        return
    
    repo_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    print(f"目标: https://github.com/{username}/{repo_name}")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print("正在 clone...")
        result = subprocess.run(
            ["git", "clone", repo_url, "website"],
            cwd=tmpdir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"❌ Clone 失败: {result.stderr}")
            return
        print("✅ Clone 成功")
        
        # 创建测试文件
        website_dir = os.path.join(tmpdir, "website")
        daily_post_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_post_dir, exist_ok=True)
        
        test_file = os.path.join(daily_post_dir, "test-from-actions.txt")
        with open(test_file, "w") as f:
            f.write("测试推送 " + os.getenv("GITHUB_ACTION", ""))
        
        # 提交推送
        subprocess.run(["git", "config", "user.name", "test-bot"], cwd=website_dir)
        subprocess.run(["git", "config", "user.email", "test@bot.com"], cwd=website_dir)
        subprocess.run(["git", "add", "daily-post/"], cwd=website_dir)
        subprocess.run(["git", "commit", "-m", "test push"], cwd=website_dir)
        push_result = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=website_dir,
            capture_output=True,
            text=True
        )
        
        if push_result.returncode == 0:
            print("✅ 推送成功")
        else:
            print(f"❌ 推送失败: {push_result.stderr}")

if __name__ == "__main__":
    test_push()
