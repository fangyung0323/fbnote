def generate_article():
    """调用 DeepSeek API 生成文章内容，回傳 dict"""
    if not DEEPSEEK_API_KEY:
        print("❌ 錯誤：DEEPSEEK_API_KEY 環境變數未設定")
        return None

    # ... 中間的程式碼不變（角色、主題、風格、結構、prompt 等）...

    print("🤖 正在呼叫 DeepSeek API 生成文章...")
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # 清理 Markdown
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        
        lines = content.strip().split("\n")
        title = lines[0].replace("#", "").strip()
        title = re.sub(r'^(標題|Title)[:：]\s*', '', title)
        if not title:
            title = f"{category}｜{subtopic[:20]}"

        print(f"✅ 文章生成成功：{title}")
        print(f"📂 類別：{category}")
        
        # 回傳 dict（為了相容新的 save_article_as_html）
        return {
            "title": title,
            "content": content,
            "category": category,
            "summary": "",  # 暫時空白，之後可由 AI 產生
            "key_points": []  # 暫時空白
        }
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None
