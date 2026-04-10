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
    """產生 daily-post 目錄的索引頁面，包含搜尋功能"""
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html":
            # 從檔名提取日期和類別
            # 格式範例: plant-20260325.html
            parts = file.replace(".html", "").split("-")
            category_key = parts[0] if len(parts) > 0 else "life"
            date_str = parts[1] if len(parts) > 1 else ""
            
            # 類別對應的中文名稱和 emoji
            category_map = {
                "plant": {"name": "植物", "emoji": "🌱"},
                "carbon": {"name": "碳盤查", "emoji": "🌍"},
                "sustainability": {"name": "永續", "emoji": "♻️"},
                "life": {"name": "生活", "emoji": "✨"}
            }
            category_info = category_map.get(category_key, {"name": "生活", "emoji": "✨"})
            
            articles.append({
                "filename": file,
                "title": file.replace(".html", "").replace("-", " / "),
                "category": category_info["name"],
                "category_emoji": category_info["emoji"],
                "date": f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:8]}" if len(date_str) == 8 else ""
            })
    
    # 按日期排序（最新的在前）
    articles.sort(key=lambda x: x["date"], reverse=True)
    
    # 產生文章列表的 HTML
    articles_html = ""
    for article in articles:
        articles_html += f'''
        <li class="article-item" data-title="{article['title'].lower()}" data-category="{article['category']}">
            <span class="article-category">{article['category_emoji']} {article['category']}</span>
            <a class="article-link" href="{article['filename']}">{article['title']}</a>
            <div class="article-date">📅 {article['date'] if article['date'] else "最新"}</div>
        </li>
        '''
    
    index_content = f'''<!DOCTYPE html>
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
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c5e2e;
            margin-bottom: 0.5rem;
            font-size: 2rem;
            text-align: center;
        }}
        .site-description {{
            text-align: center;
            color: #7f8c6d;
            margin-bottom: 2rem;
            font-size: 0.95rem;
        }}
        
        /* 搜尋框區域 */
        .search-section {{
            margin-bottom: 2rem;
        }}
        .search-box {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}
        .search-input {{
            flex: 1;
            padding: 0.8rem 1rem;
            border: 1px solid #e0dbd0;
            border-radius: 30px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
            background: white;
        }}
        .search-input:focus {{
            border-color: #4a7c59;
            box-shadow: 0 0 0 3px rgba(74, 124, 89, 0.1);
        }}
        .search-input::placeholder {{
            color: #bbb5a8;
        }}
        .search-clear {{
            padding: 0.8rem 1.2rem;
            background: #e8e5dd;
            border: none;
            border-radius: 30px;
            cursor: pointer;
            font-size: 0.9rem;
            color: #4a7c59;
            transition: background 0.2s;
        }}
        .search-clear:hover {{
            background: #ddd8cc;
        }}
        
        /* 分類篩選按鈕 */
        .filter-buttons {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }}
        .filter-btn {{
            padding: 0.4rem 1rem;
            background: #e8e5dd;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85rem;
            color: #4a7c59;
            transition: all 0.2s;
        }}
        .filter-btn.active {{
            background: #4a7c59;
            color: white;
        }}
        .filter-btn:hover {{
            background: #c5c0b2;
        }}
        
        /* 搜尋結果統計 */
        .result-stats {{
            font-size: 0.85rem;
            color: #7f8c6d;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e0dbd0;
        }}
        
        /* 文章列表 */
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
        .article-category {{
            display: inline-block;
            font-size: 0.75rem;
            color: #4a7c59;
            background: #e8f0e6;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            margin-bottom: 0.5rem;
        }}
        .article-link {{
            font-size: 1.2rem;
            font-weight: 500;
            color: #2c5e2e;
            text-decoration: none;
            display: block;
            margin-bottom: 0.5rem;
        }}
        .article-link:hover {{
            text-decoration: underline;
        }}
        .article-date {{
            color: #7f8c6d;
            font-size: 0.8rem;
        }}
        
        /* 無結果訊息 */
        .no-results {{
            text-align: center;
            padding: 3rem;
            color: #7f8c6d;
            background: white;
            border-radius: 12px;
        }}
        
        /* 底部導航 */
        .bottom-nav {{
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #e0dbd0;
        }}
        .bottom-nav a {{
            color: #4a7c59;
            text-decoration: none;
            margin: 0 0.5rem;
        }}
        .bottom-nav a:hover {{
            text-decoration: underline;
        }}
        
        @media (max-width: 600px) {{
            body {{ padding: 1rem; }}
            .search-box {{ flex-direction: column; }}
            .search-clear {{ align-self: flex-end; }}
            .filter-buttons {{ justify-content: center; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 蕨積每日文章</h1>
        <div class="site-description">
            植物・永續・碳盤查・生活 — 每天一篇，與你一起成長
        </div>
        
        <!-- 搜尋區域 -->
        <div class="search-section">
            <div class="search-box">
                <input type="text" id="searchInput" class="search-input" placeholder="🔍 搜尋文章標題...">
                <button id="clearSearch" class="search-clear">清除</button>
            </div>
            <div class="filter-buttons" id="filterButtons">
                <button class="filter-btn active" data-category="all">📋 全部</button>
                <button class="filter-btn" data-category="植物">🌱 植物</button>
                <button class="filter-btn" data-category="碳盤查">🌍 碳盤查</button>
                <button class="filter-btn" data-category="永續">♻️ 永續</button>
                <button class="filter-btn" data-category="生活">✨ 生活</button>
            </div>
            <div class="result-stats" id="resultStats">共 <span id="articleCount">{len(articles)}</span> 篇文章</div>
        </div>
        
        <!-- 文章列表 -->
        <ul class="article-list" id="articleList">
            {articles_html}
        </ul>
        
        <!-- 無結果提示（預設隱藏） -->
        <div id="noResults" class="no-results" style="display: none;">
            😢 沒有找到相關文章<br>
            試試其他關鍵字吧！
        </div>
        
        <!-- 底部導航 -->
        <div class="bottom-nav">
            <a href="./shop.html">🌱 植物選品</a>
            <span>|</span>
            <a href="./consulting.html">💚 綠色顧問</a>
        </div>
    </div>
    
    <script>
        // 取得 DOM 元素
        const searchInput = document.getElementById('searchInput');
        const clearBtn = document.getElementById('clearSearch');
        const articleList = document.getElementById('articleList');
        const articleItems = document.querySelectorAll('.article-item');
        const noResultsDiv = document.getElementById('noResults');
        const articleCountSpan = document.getElementById('articleCount');
        const filterBtns = document.querySelectorAll('.filter-btn');
        
        let currentCategory = 'all';
        let currentSearchTerm = '';
        
        // 更新文章顯示
        function updateDisplay() {{
            let visibleCount = 0;
            const searchTerm = currentSearchTerm.toLowerCase().trim();
            
            articleItems.forEach(item => {{
                const title = item.getAttribute('data-title') || '';
                const category = item.getAttribute('data-category') || '';
                
                // 檢查分類篩選
                let categoryMatch = false;
                if (currentCategory === 'all') {{
                    categoryMatch = true;
                }} else {{
                    categoryMatch = category === currentCategory;
                }}
                
                // 檢查搜尋關鍵字（比對標題）
                let searchMatch = false;
                if (searchTerm === '') {{
                    searchMatch = true;
                }} else {{
                    searchMatch = title.includes(searchTerm);
                }}
                
                // 決定是否顯示
                if (categoryMatch && searchMatch) {{
                    item.style.display = '';
                    visibleCount++;
                }} else {{
                    item.style.display = 'none';
                }}
            }});
            
            // 更新統計
            articleCountSpan.textContent = visibleCount;
            
            // 顯示/隱藏無結果提示
            if (visibleCount === 0) {{
                noResultsDiv.style.display = 'block';
                articleList.style.display = 'none';
            }} else {{
                noResultsDiv.style.display = 'none';
                articleList.style.display = 'block';
            }}
        }}
        
        // 搜尋輸入事件
        searchInput.addEventListener('input', function(e) {{
            currentSearchTerm = e.target.value;
            updateDisplay();
        }});
        
        // 清除搜尋
        clearBtn.addEventListener('click', function() {{
            searchInput.value = '';
            currentSearchTerm = '';
            updateDisplay();
            searchInput.focus();
        }});
        
        // 分類篩選
        filterBtns.forEach(btn => {{
            btn.addEventListener('click', function() {{
                // 更新按鈕樣式
                filterBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                // 更新當前分類
                currentCategory = this.getAttribute('data-category');
                updateDisplay();
            }});
        }});
        
        // 初始化顯示
        updateDisplay();
    </script>
</body>
</html>'''
    
    index_path = os.path.join(daily_post_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    print("📑 已更新 daily-post/index.html（含搜尋功能）")


if __name__ == "__main__":
    main()
