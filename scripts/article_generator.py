def generate_article():
    """调用 DeepSeek API 生成文章内容，回傳 dict（包含 title, content, category, summary, key_points）"""
    if not DEEPSEEK_API_KEY:
        print("❌ 錯誤：DEEPSEEK_API_KEY 環境變數未設定")
        return None

    category = get_today_category()
    custom = get_custom_config()

    # 固定角色（蕨積風格）
    role_prompt = "你是「蕨積內容編輯」，習慣用生活觀察的方式描述空間、植物與人的關係。"

    # ==================== 主題來源 ====================
    news_context = None
    subtopic = None
    
    if custom["topics"].get(category):
        subtopic = custom["topics"][category]
        print(f"🌱 手動主題：{subtopic}")
    else:
        news_data = get_news_based_topic(category)
        
        if news_data:
            subtopic = news_data["topic"]
            news_context = news_data["news_context"]
            print(f"📰 新聞主題：{subtopic}")
            print(f"📰 新聞來源：{news_data.get('source', '未知')} ({news_data.get('date', '日期不詳')})")
        else:
            subtopic = random.choice(SUB_TOPICS.get(category, ["一般主題"]))
            print(f"🌱 隨機主題（內建）：{subtopic}")

    # ==================== 新聞區塊 ====================
    if news_context:
        news_section = f"""
【參考新聞】
{news_context}

【使用方式（重要）】
- 將新聞作為「背景靈感」
- 可以輕微提及，但不要解釋新聞
- 不要整理、分析或評論新聞
- 重點仍然是生活觀察
"""
    else:
        news_section = """
【寫作參考】
目前無特定新聞資料，請基於主題進行生活觀察書寫。
"""

    # ==================== Prompt ====================
    prompt = f"""
請根據以下主題，撰寫一篇「生活觀察型文章」。

【主題】
{subtopic}

{news_section}

【寫作方式】
- 從一個生活中的小場景或感受開始
- 描述人與空間、環境、植物之間的關係
- 不要急著解釋或教學
- 讓讀者自己感覺到變化

【語氣】
- 自然、安靜、有畫面感
- 像是在記錄一個觀察
- 不要有專家感

【嚴格限制】
- 不要使用「首先、其次、最後」
- 不要條列式內容
- 不要寫成教學文
- 不要出現「可以從以下幾點」
- 不要強調數據或專業術語
- 不要出現「總之」「綜上所述」
- 不要提到 AI、ChatGPT

【Email 使用（很重要）】
title：
- 12字內
- 有畫面感（不要像新聞標題）

summary：
- 20~30字
- 像一句觀察

key_points：
- 3句話
- 每句不超過15字
- 像感受，不是知識

【輸出格式（非常重要）】
請「只輸出 JSON」，不要包含任何說明文字。

JSON 結構如下：
{{
  "title": "",
  "summary": "",
  "key_points": ["", "", ""],
  "content": ""
}}

【HTML 規則】
- content 使用 HTML（<p> 為主）
- 不要使用 Markdown（例如 ** 或 #）

【長度】
400～700字

結尾加上：
🌿 蕨積 - 讓生活多一點綠
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": role_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 2500,
        "response_format": {"type": "json_object"}
    }

    print("🤖 正在呼叫 DeepSeek API 生成文章...")

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()

        article_data = json.loads(data["choices"][0]["message"]["content"])

        title = article_data.get("title", "")
        summary = article_data.get("summary", "")
        key_points = article_data.get("key_points", [])
        content = article_data.get("content", "")

        # 清除 markdown 殘留
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

        # fallback title
        if not title:
            title = f"{category}｜{subtopic[:20]}"

        # key_points 修正
        if not isinstance(key_points, list):
            key_points = []

        fallback_points = [
            "有些變化很慢",
            "空間會影響人",
            "綠其實一直都在"
        ]

        while len(key_points) < 3:
            key_points.append(random.choice(fallback_points))

        key_points = key_points[:3]

        # 字數計算
        content_text = re.sub(r'<[^>]+>', '', content)
        word_count = len(content_text)

        print(f"✅ 文章生成成功：{title}")
        print(f"📂 類別：{category}")
        print(f"📏 文章長度：{word_count} 字")

        if word_count < 400:
            print(f"⚠️ 警告：文章太短（{word_count}字）")
        elif word_count < 600:
            print(f"📌 長度略低但可接受")
        else:
            print(f"✨ 長度正常")

        return {
            "title": title,
            "content": content,
            "category": category,
            "summary": summary,
            "key_points": key_points
        }

    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失敗：{e}")
        if 'data' in locals():
            print(data["choices"][0]["message"]["content"][:500])
        return None

    except requests.exceptions.Timeout:
        print("❌ API 呼叫超時")
        return None

    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None
