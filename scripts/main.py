def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面"""
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html" and len(file) >= 10 and file[4] == '-' and file[7] == '-':
            filepath = os.path.join(daily_post_dir, file)
            
            category = "未分類"
            title = ""
            content_html = ""
            date_str = file[:10]
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    full_content = f.read()
                    match_cat = re.search(r'<div class="article-category">📌 (.+?)</div>', full_content)
                    if match_cat:
                        category = match_cat.group(1)
                    match_title = re.search(r'<h1 class="article-title">(.+?)</h1>', full_content)
                    if match_title:
                        title = match_title.group(1)
                    match_content = re.search(r'<div class="article-content">(.*?)</div>', full_content, re.DOTALL)
                    if match_content:
                        content_html = match_content.group(1)
            except:
                title = file.replace(".html", "").replace(date_str + "-", "").replace("-", " / ")
            
            articles.append({
                "filename": file,
                "date": date_str,
                "title": title,
                "category": category,
                "content": content_html
            })
    
    articles.sort(key=lambda x: x["date"], reverse=True)
    
    if not articles:
        empty_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蕨積每日文章</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600;900&family=Noto+Sans+TC:wght@300;400;500&family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&display=swap" rel="stylesheet">
    <style>{get_template_styles()}</style>
</head>
<body>
    <div id="nav-placeholder"></div>
    <main class="content">
        <div style="text-align:center;padding:60px 20px;">
            <h1 style="font-family:'Noto Serif TC',serif;color:var(--moss);">🌿 蕨積每日文章</h1>
            <p style="color:var(--stone);margin-top:1rem;">📭 目前還沒有文章，等待機器人發文中...</p>
        </div>
    </main>
    {get_footer_html()}
    <script>{get_nav_script()}</script>
</body>
</html>"""
        with open(os.path.join(daily_post_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(empty_html)
        print("📑 已更新 daily-post/index.html (無文章)")
        return
    
    latest = articles[0]
    past_articles = articles[1:]
    
    # 按月歸檔
    archive_by_month = {}
    for article in past_articles:
        month_key = article["date"][:7]
        if month_key not in archive_by_month:
            archive_by_month[month_key] = []
        archive_by_month[month_key].append(article)
    
    # 生成過往文章列表 HTML
    past_list_html = ""
    for article in past_articles[:30]:
        cat_color = CATEGORY_COLORS.get(article["category"], "#6c757d")
        past_list_html += f"""
                        <li class="past-item" data-category="{article['category']}">
                            <span class="past-badge" style="background: {cat_color};">{article['category']}</span>
                            <a class="past-link" href="{article['filename']}">{article['title']}</a>
                            <div class="past-meta">📅 {article['date']}</div>
                        </li>"""
    
    # 生成歸檔 HTML
    archive_html = ""
    sorted_months = sorted(archive_by_month.keys(), reverse=True)
    for month in sorted_months:
        month_display = f"{month[:4]}年{int(month[5:7])}月"
        archive_html += f"""
                    <div class="archive-month">
                        <div class="archive-month-title">{month_display}</div>
                        <ul class="archive-list">"""
        for article in archive_by_month[month][:8]:
            archive_html += f'<li><a href="{article["filename"]}">{article["title"][:25]}{"..." if len(article["title"]) > 25 else ""}</a></li>'
        if len(archive_by_month[month]) > 8:
            archive_html += f'<li><a href="#" style="color:#aaa;">... 共{len(archive_by_month[month])}篇</a></li>'
        archive_html += """
                        </ul>
                    </div>"""
    
    # 最新文章類別顏色
    latest_cat_color = CATEGORY_COLORS.get(latest['category'], "#6c757d")
    
    # 生成完整 HTML（使用普通字串拼接）
    index_html = '<!DOCTYPE html>\n'
    index_html += '<html lang="zh-TW">\n'
    index_html += '<head>\n'
    index_html += '    <meta charset="UTF-8">\n'
    index_html += '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    index_html += '    <title>蕨積每日文章 - 植物・永續・碳盤查・生活</title>\n'
    index_html += '    <link rel="preconnect" href="https://fonts.googleapis.com">\n'
    index_html += '    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600;900&family=Noto+Sans+TC:wght@300;400;500&family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&display=swap" rel="stylesheet">\n'
    index_html += '    <script src="https://unpkg.com/lucide@latest"></script>\n'
    index_html += '    <style>' + get_template_styles() + '\n'
    index_html += '    /* ===== 每日文章專用樣式 ===== */\n'
    index_html += '    .daily-container { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }\n'
    index_html += '    .page-header { text-align: center; margin-bottom: 2rem; }\n'
    index_html += '    .page-header h1 { color: var(--moss); font-size: 2rem; font-family: "Noto Serif TC", serif; }\n'
    index_html += '    .page-header p { color: var(--stone); margin-top: 0.5rem; }\n'
    index_html += '    \n'
    index_html += '    .categories {\n'
    index_html += '        display: flex;\n'
    index_html += '        justify-content: center;\n'
    index_html += '        gap: 1rem;\n'
    index_html += '        flex-wrap: wrap;\n'
    index_html += '        margin-bottom: 2rem;\n'
    index_html += '    }\n'
    index_html += '    .category-btn {\n'
    index_html += '        padding: 0.5rem 1.5rem;\n'
    index_html += '        border-radius: 30px;\n'
    index_html += '        border: none;\n'
    index_html += '        cursor: pointer;\n'
    index_html += '        font-size: 0.9rem;\n'
    index_html += '        font-weight: 500;\n'
    index_html += '        transition: transform 0.2s;\n'
    index_html += '        background: #e8e0d8;\n'
    index_html += '        color: #4a5b4e;\n'
    index_html += '    }\n'
    index_html += '    .category-btn:hover { transform: translateY(-2px); }\n'
    index_html += '    .category-btn.active { background: #4a7c59; color: white; }\n'
    index_html += '    \n'
    index_html += '    .two-columns { display: flex; gap: 2rem; flex-wrap: wrap; }\n'
    index_html += '    .main-col { flex: 3; min-width: 250px; }\n'
    index_html += '    .sidebar-col { flex: 1; min-width: 200px; background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); height: fit-content; }\n'
    index_html += '    \n'
    index_html += '    .latest-article {\n'
    index_html += '        background: white;\n'
    index_html += '        border-radius: 16px;\n'
    index_html += '        padding: 2rem;\n'
    index_html += '        margin-bottom: 2rem;\n'
    index_html += '        box-shadow: 0 2px 12px rgba(0,0,0,0.08);\n'
    index_html += '    }\n'
    index_html += '    .latest-category {\n'
    index_html += '        display: inline-block;\n'
    index_html += '        background: ' + latest_cat_color + ';\n'
    index_html += '        color: white;\n'
    index_html += '        padding: 0.2rem 0.8rem;\n'
    index_html += '        border-radius: 20px;\n'
    index_html += '        font-size: 0.8rem;\n'
    index_html += '        margin-bottom: 1rem;\n'
    index_html += '    }\n'
    index_html += '    .latest-title { font-size: 1.8rem; color: var(--moss); margin-bottom: 0.5rem; }\n'
    index_html += '    .latest-date { color: var(--stone); margin-bottom: 1.5rem; font-size: 0.9rem; }\n'
    index_html += '    .latest-content { line-height: 1.8; }\n'
    index_html += '    .read-more { display: inline-block; margin-top: 1rem; color: var(--fern); text-decoration: none; font-weight: 500; }\n'
    index_html += '    \n'
    index_html += '    .section-title { font-size: 1.2rem; color: var(--moss); border-bottom: 2px solid #e0d6cc; padding-bottom: 0.5rem; margin-bottom: 1rem; }\n'
    index_html += '    .past-list { list-style: none; }\n'
    index_html += '    .past-item { margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #f0e8e0; }\n'
    index_html += '    .past-link { font-size: 0.95rem; font-weight: 500; color: var(--fern); text-decoration: none; display: block; }\n'
    index_html += '    .past-link:hover { text-decoration: underline; }\n'
    index_html += '    .past-meta { font-size: 0.7rem; color: #aaa; margin-top: 0.25rem; }\n'
    index_html += '    .past-badge { display: inline-block; font-size: 0.65rem; padding: 0.1rem 0.5rem; border-radius: 12px; color: white; margin-right: 0.5rem; }\n'
    index_html += '    .archive-month { margin-bottom: 1rem; }\n'
    index_html += '    .archive-month-title { font-weight: 600; color: var(--moss); margin-bottom: 0.5rem; }\n'
    index_html += '    .archive-list { list-style: none; padding-left: 0.5rem; }\n'
    index_html += '    .archive-list li { margin-bottom: 0.3rem; }\n'
    index_html += '    .archive-list a { color: var(--stone); text-decoration: none; font-size: 0.85rem; }\n'
    index_html += '    .archive-list a:hover { color: var(--fern); text-decoration: underline; }\n'
    index_html += '    \n'
    index_html += '    @media (max-width: 768px) {\n'
    index_html += '        .two-columns { flex-direction: column; }\n'
    index_html += '        .latest-title { font-size: 1.4rem; }\n'
    index_html += '        .daily-container { padding: 0 1rem; }\n'
    index_html += '    }\n'
    index_html += '    </style>\n'
    index_html += '</head>\n'
    index_html += '<body>\n'
    index_html += '    <div id="nav-placeholder"></div>\n'
    index_html += '    \n'
    index_html += '    <main class="content">\n'
    index_html += '        <div class="daily-container">\n'
    index_html += '            <div class="page-header">\n'
    index_html += '                <h1>🌿 蕨積每日文章</h1>\n'
    index_html += '                <p>植物・永續・碳盤查・生活 — 每天一篇，與你一起成長</p>\n'
    index_html += '            </div>\n'
    index_html += '            \n'
    index_html += '            <div class="categories">\n'
    index_html += '                <button class="category-btn active" data-category="all">📋 全部</button>\n'
    index_html += '                <button class="category-btn" data-category="植物">🌿 植物</button>\n'
    index_html += '                <button class="category-btn" data-category="永續">♻️ 永續</button>\n'
    index_html += '                <button class="category-btn" data-category="碳盤查">📊 碳盤查</button>\n'
    index_html += '                <button class="category-btn" data-category="生活">🏡 生活</button>\n'
    index_html += '            </div>\n'
    index_html += '            \n'
    index_html += '            <div class="two-columns">\n'
    index_html += '                <div class="main-col">\n'
    index_html += '                    <div class="latest-article">\n'
    index_html += '                        <div class="latest-category">📌 ' + latest['category'] + '</div>\n'
    index_html += '                        <h1 class="latest-title">' + latest['title'] + '</h1>\n'
    index_html += '                        <div class="latest-date">📅 ' + latest['date'] + '</div>\n'
    index_html += '                        <div class="latest-content">' + latest['content'] + '</div>\n'
    index_html += '                        <a href="' + latest['filename'] + '" class="read-more">🔗 查看獨立頁面 →</a>\n'
    index_html += '                    </div>\n'
    index_html += '                    \n'
    index_html += '                    <div class="section-title">📖 過往文章</div>\n'
    index_html += '                    <ul class="past-list" id="pastList">\n'
    index_html += past_list_html
    index_html += '                    </ul>\n'
    index_html += '                </div>\n'
    index_html += '                \n'
    index_html += '                <div class="sidebar-col">\n'
    index_html += '                    <div class="section-title">📚 歷史歸檔</div>\n'
    index_html += archive_html
    index_html += '                </div>\n'
    index_html += '            </div>\n'
    index_html += '        </div>\n'
    index_html += '    </main>\n'
    index_html += '    \n'
    index_html += get_footer_html()
    index_html += '    \n'
    index_html += '    <script>\n'
    index_html += get_nav_script()
    index_html += '\n'
    index_html += '    // 分類篩選功能\n'
    index_html += '    (function() {\n'
    index_html += '        const filterBtns = document.querySelectorAll(".category-btn");\n'
    index_html += '        const pastItems = document.querySelectorAll("#pastList .past-item");\n'
    index_html += '        \n'
    index_html += '        function filterArticles() {\n'
    index_html += '            const activeBtn = document.querySelector(".category-btn.active");\n'
    index_html += '            const category = activeBtn ? activeBtn.getAttribute("data-category") : "all";\n'
    index_html += '            \n'
    index_html += '            pastItems.forEach(item => {\n'
    index_html += '                if (category === "all" || item.getAttribute("data-category") === category) {\n'
    index_html += '                    item.style.display = "";\n'
    index_html += '                } else {\n'
    index_html += '                    item.style.display = "none";\n'
    index_html += '                }\n'
    index_html += '            });\n'
    index_html += '        }\n'
    index_html += '        \n'
    index_html += '        filterBtns.forEach(btn => {\n'
    index_html += '            btn.addEventListener("click", function() {\n'
    index_html += '                filterBtns.forEach(b => b.classList.remove("active"));\n'
    index_html += '                this.classList.add("active");\n'
    index_html += '                filterArticles();\n'
    index_html += '            });\n'
    index_html += '        });\n'
    index_html += '        \n'
    index_html += '        filterArticles();\n'
    index_html += '    })();\n'
    index_html += '    </script>\n'
    index_html += '</body>\n'
    index_html += '</html>'
    
    index_path = os.path.join(daily_post_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"📑 已更新 daily-post/index.html (共 {len(articles)} 篇文章)")
