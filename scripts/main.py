#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from categories import CATEGORIES, get_today_category
from article_generator import ArticleGenerator
from image_generator import ImageGenerator
from website_publisher import WebsitePublisher

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
    print(f"📝 今日類別：{category_info['name']} {category_info['emoji']}")
    
    # 初始化各模組
    article_gen = ArticleGenerator(deepseek_key)
    image_gen = ImageGenerator(deepseek_key)
    publisher = WebsitePublisher(os.getenv("SITE_PATH", "/github/workspace"))
    
    # 1. 生成文章
    print("✍️  生成文章中...")
    article = article_gen.generate(today_category, category_info)
    
    if not article:
        print("❌ 文章生成失敗")
        sys.exit(1)
    
    print(f"✅ 文章生成完成：{article['title']}")
    
    # 2. 生成圖片
    print("🎨 生成配圖中...")
    image_path = image_gen.generate(category_info["image_prompt"], today_category)
    print(f"✅ 圖片生成完成：{image_path}")
    
    # 3. 發布到網站
    print("📤 發布到網站...")
    url = publisher.publish(article, image_path)
    print(f"✅ 發布完成：{url}")
    
    print("🎉 蕨積機器人執行完畢！")

if __name__ == "__main__":
    main()
