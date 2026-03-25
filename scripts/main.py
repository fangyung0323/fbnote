# scripts/main.py - 改寫為單次執行版
#!/usr/bin/env python3
import os
import sys
import subprocess
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
    
    # 3. 產生 HTML 檔案（儲存到 articles/ 目錄）
    html_path = generate_html(article, image_path)
    print(f"✅ 文章已生成：{html_path}")
    
    # 4. 提交並推送至 Git（Render Cron Job 需有寫入權限）
    commit_and_push()
    
    print("🎉 執行完畢！")

def commit_and_push():
    """提交變更並推送到 Git 倉庫"""
    subprocess.run(["git", "config", "user.name", "render-cron"], check=False)
    subprocess.run(["git", "config", "user.email", "render@local"], check=False)
    subprocess.run(["git", "add", "articles/", "images/"], check=False)
    subprocess.run(["git", "commit", "-m", f"每日發文 {datetime.now().strftime('%Y-%m-%d')}"], check=False)
    subprocess.run(["git", "push"], check=False)

if __name__ == "__main__":
    main()
