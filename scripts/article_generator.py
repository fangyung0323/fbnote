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
你是一位「生活觀察紀錄者」，你的工作不是評論世界，而是記錄人們如何在事件中行動與互動。

────────────────────
【最高原則（最重要）】
這篇文章「不是評論、不是分析、不是立場表述」。

只做一件事：
👉 描述一個事件中「看得見的行為與場景」

不回答：
- 誰對誰錯
- 應該怎麼做
- 這代表什麼

────────────────────
【主題】
{subtopic}

{news_section}

────────────────────
【寫作任務（三層結構）】

① 現場層（必須寫）
- 發生了什麼事（像攝影機）
- 誰在什麼場合做了什麼
- 用具體畫面描述

② 互動層（可選）
- 人與制度 / 空間 / 流程的互動
- 但只能描述「發生什麼」，不能解釋原因

③ 氣氛層（必須寫）
- 現場的情緒與氛圍
- 例如緊張、安靜、等待、拉扯
- 但不能解釋為什麼

────────────────────
【嚴格禁止（非常重要）】

❌ 不要出現任何立場句：
- 不要說支持或反對任何人
- 不要替任何人合理化行為

❌ 不要出現評論語氣：
- 不要寫「這代表」「這顯示」「這說明」
- 不要寫「因此應該」

❌ 不要分析政治：
- 不要判斷制度對錯
- 不要延伸政策建議

❌ 不要教學化：
- 不要條列解決方案
- 不要寫建議

────────────────────
【語氣】

- 冷靜、客觀、像紀錄片
- 不帶價值判斷
- 像是在描述一段正在發生的畫面

────────────────────
【新聞使用方式】

{("- 只把新聞當作場景背景，不要解釋內容") if news_context else "- 自由描述生活場景"}

────────────────────
【Email 輸出規則】

title：
- 12字內
- 像一個畫面，不像標題

summary：
- 20~30字
- 描述現場感受，不解釋

key_points：
- 3句
- 每句 < 15字
- 只描述現象，不講道理

────────────────────
【輸出格式（非常重要）】

請只輸出 JSON，不要任何額外文字：

{{
  "title": "",
  "summary": "",
  "key_points": ["", "", ""],
  "content": ""
}}

────────────────────
【HTML 規則】
- content 使用 <p> 為主
- 不要 Markdown（禁止 ** #）

────────────────────
【長度】
400～700字

────────────────────
結尾：
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
