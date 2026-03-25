def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面"""
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html":
            articles.append(file)
    
    articles.sort(reverse=True)  # 最新的在前
    
    if not articles:
        return
    
    # 改用普通字符串，避免 f-string 中的反斜杠問題
    index_content = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蕨積每日文章</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #2c3e2f;
            background-color: #faf8f4;
            padding: 2rem;
        }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #2c5e2e; margin-bottom: 2rem; font-size: 2rem; }
        .article-list { list-style: none; padding: 0; }
        .article-item {
            margin: 1rem 0;
            padding: 1.2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .article-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .article-link {
            font-size: 1.2rem;
            font-weight: 500;
            color: #4a7c59;
            text-decoration: none;
        }
        .article-link:hover { text-decoration: underline; }
        .article-date {
            color: #7f8c6d;
            font-size: 0.85rem;
            margin-top: 0.5rem;
        }
        .back-link {
            display: inline-block;
            margin-top: 2rem;
            color: #4a7c59;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 蕨積每日文章</h1>
        <ul class="article-list">"""
    
    # 手動添加文章列表（避免 f-string 中的反斜杠）
    for article in articles:
        display_title = article.replace(".html", "").replace("-", " / ")
        date_part = article.replace(".html", "").split("-")[-1] if "-" in article else "最新"
        index_content += f'<li class="article-item"><a class="article-link" href="{article}">{display_title}</a><div class="article-date">📅 {date_part}</div></li>'
    
    index_content += """
        </ul>
        <a href="/" class="back-link">← 返回首頁</a>
    </div>
</body>
</html>"""
    
    index_path = os.path.join(daily_post_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
    print("📑 已更新 daily-post/index.html")
