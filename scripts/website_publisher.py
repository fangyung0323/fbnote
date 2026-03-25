import os
import json
from datetime import datetime
from typing import Dict

class WebsitePublisher:
    def __init__(self, site_path: str):
        self.site_path = site_path
        self.articles_path = os.path.join(site_path, "articles")
        os.makedirs(self.articles_path, exist_ok=True)
    
    def publish(self, article: Dict, image_path: str) -> str:
        """生成HTML檔案並發布到靜態網站"""
        
        # 生成 slug（URL 友好格式）
        slug = f"{article['category_key']}-{datetime.now().strftime('%Y%m%d')}"
        html_filename = f"{slug}.html"
        html_path = os.path.join(self.articles_path, html_filename)
        
        # 完整的 HTML 頁面
        html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{article['summary']}">
    <title>{article['title']} - 蕨積</title>
    
    <!-- Open Graph 標籤（社群分享用）-->
    <meta property="og:title" content="{article['title']}">
    <meta property="og:description" content="{article['summary']}">
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
            font-size: 2.5rem;
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
            font-size: 1.8rem;
        }}
        
        .article-content p {{
            margin-bottom: 1.2rem;
        }}
        
        .article-content ul, .article-content ol {{
            margin: 1rem 0 1rem 2rem;
        }}
        
        .tags {{
            margin: 2rem 0;
            padding-top: 1rem;
            border-top: 1px solid #e0dbd0;
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
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            h1 {{
                font-size: 1.8rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <article>
            <div class="article-header">
                <div class="category-badge">{article['category']} {self._get_emoji(article['category_key'])}</div>
                <h1>{article['title']}</h1>
                <div class="article-meta">
                    發布日期：{article['date']} | 
                    <span class="reading-time">📖 {article['reading_time']} 分鐘閱讀</span>
                </div>
            </div>
            
            <img src="{image_path}" alt="{article['title']}" class="featured-image">
            
            <div class="article-content">
                {article['content']}
            </div>
            
            <div class="tags">
                <strong>標籤：</strong>
                {''.join([f'<span class="tag">#{tag}</span>' for tag in article['tags']])}
            </div>
        </article>
    </div>
</body>
</html>"""
        
        # 寫入檔案
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # 同時更新索引頁面（可選）
        self._update_index()
        
        return f"/articles/{html_filename}"
    
    def _get_emoji(self, category_key):
        emojis = {
            "plant": "🌱",
            "carbon": "🌍",
            "sustainability": "♻️",
            "life": "✨"
        }
        return emojis.get(category_key, "📝")
    
    def _update_index(self):
        """更新文章列表頁面"""
        # 獲取所有文章
        articles = []
        for filename in os.listdir(self.articles_path):
            if filename.endswith(".html") and filename != "index.html":
                articles.append(filename)
        
        # 按日期排序（最新的在前）
        articles.sort(reverse=True)
        
        # 生成文章列表
        index_path = os.path.join(self.articles_path, "index.html")
        index_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>蕨積文章列表</title>
    <style>
        body {{ font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 2rem; background: #faf8f4; }}
        h1 {{ color: #2c5e2e; }}
        .article-list {{ list-style: none; padding: 0; }}
        .article-item {{ margin-bottom: 1rem; padding: 1rem; background: white; border-radius: 8px; }}
        .article-date {{ color: #7f8c6d; font-size: 0.8rem; }}
        a {{ color: #4a7c59; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>蕨積 - 最新文章</h1>
    <ul class="article-list">
        {''.join([f'<li class="article-item"><a href="{article}">{article.replace(".html", "")}</a></li>' for article in articles[:20]])}
    </ul>
</body>
</html>"""
        
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content)
