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
請根據以下主題，撰寫一篇「純生活觀察紀錄」。

【主題】
{subtopic}

{news_section}

────────────────────
【核心任務】

你不是作者，你是「鏡頭」。

你不解釋、不分析、不評論，只負責「拍下正在發生的畫面」。

────────────────────
【寫作方式：鏡頭語言（非常重要）】

整篇文章必須像影像紀錄，而不是文章。

請使用以下三種鏡頭語言：

①【遠景（建立空間）】
- 描述地點、環境、時間
- 像電影開場鏡頭
- 不可出現情緒與判斷

②【中景（人物與行為）】
- 描述人正在做什麼
- 動作要具體（走、停、說話、看）
- 可以有對話，但不能解釋對話

③【特寫（細節停留）】
- 聚焦一個小物件、聲音、動作或瞬間
- 放慢時間
- 不要延伸意義

────────────────────
【嚴格禁止（很重要）】

- 禁止解釋原因
- 禁止分析事件
- 禁止社會評論
- 禁止價值判斷（好/壞/對/錯）
- 禁止總結
- 禁止建議讀者行動
- 禁止使用「這代表」「這意味著」
- 禁止寫成新聞或報導
- 禁止條列式

────────────────────
【語氣要求】

- 像攝影機，不像評論者
- 不要整理世界，只要呈現世界
- 保留沉默與空白
- 允許「沒有答案」

────────────────────
【新聞使用方式】

{("- 新聞只能當作背景畫面\n- 不可解釋、不評論、不引用立場\n- 像遠方正在發生的事情") if news_context else "- 自由拍攝生活場景"}

────────────────────
【輸出格式（嚴格）】

只輸出 JSON：

{{
  "title": "",
  "summary": "",
  "key_points": ["", "", ""],
  "content": ""
}}

────────────────────
【title 規則】
- 12字內
- 像畫面，不像標題
- 可以像「一個鏡頭」

【summary 規則】
- 一句話
- 像一個瞬間，不是結論

【key_points 規則】
- 三個「畫面片段」
- 每個不超過15字
- 禁止知識化

【content 規則】
- 使用 HTML（<p>）
- 一段一個鏡頭感
- 禁止 Markdown

────────────────────
【長度】
500～800字

────────────────────
【結尾固定】

<br>🌿 蕨積 - 讓生活多一點綠
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
