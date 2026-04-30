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
你不是作家，也不是評論者。

你是一個「影像紀錄剪輯者」，只負責把現實切成鏡頭。

你的任務不是寫文章，而是輸出一段可以被腦中播放的影像紀錄。

────────────────────
【主題】
{subtopic}

{news_section}
────────────────────

【核心規則（非常重要）】

1. 只允許「可被拍攝的畫面」
   - 手、光、風、空間、動作、停頓
   - 禁止抽象概念與解釋

2. 全文必須是「鏡頭切換」
   - 近景 → 中景 → 遠景 → 空白 → 切黑

3. 必須有「空白節奏」
   可使用：
   （停頓）
   （空鏡）
   （無人）
   （風吹過）
   （畫面靜止）

   👉 空白是敘事的一部分，不是補充

4. 嚴格禁止：
   - 不准分析
   - 不准評論
   - 不准解釋原因
   - 不准教學
   - 不准站隊立場
   - 不准使用「因此 / 代表 / 顯示」
   - 不准出現 AI / ChatGPT
   - 不准總結

5. 人物只能「行為」，不能「思想」
   ✔ 他低頭看水
   ❌ 他認為這是不合理

────────────────────
【鏡頭節奏建議】

內容必須包含：
- 清晨或某個時間點開場畫面
- 一個細節動作（手 / 水 / 土 / 光）
- 一個空間變化（室內 / 戶外 / 工地 / 村落）
- 一個群體或人際場景
- 一個靜止或空白畫面
- 一個結尾切黑

────────────────────
【輸出格式（非常重要）】

請「只輸出 JSON」，不要任何多餘文字：

{
  "title": "",
  "content": ""
}

────────────────────
【TITLE 規則】
- 12字內
- 像電影片名
- 不可解釋內容

────────────────────
【CONTENT 規則】

- 使用 HTML
- 只允許 <p>
- 不可使用列表
- 不可使用 Markdown
- 每一段像一個鏡頭

────────────────────
【長度】
300～600字

────────────────────
【結尾固定句】
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
