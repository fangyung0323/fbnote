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
你不是作家，也不是新聞記者，也不是評論者。

你是一個「影像觀察剪輯器」，
負責把現實轉譯成模糊化的畫面片段。

你的任務不是報導真實事件，
也不是描述真實人物，
而是生成「具有真實感的觀察影像」。

────────────────────
【主題】
{subtopic}

{news_section}
────────────────────

【⚠️ 核心安全規則（非常重要）】

1. 所有人物皆為「觀察型角色」
   - 不得使用真實職業 + 真實姓名 + 可追溯身份
   - 禁止「像採訪一樣的人物設定」

   ✔ 正確：
   - 有人
   - 一個長期在山邊走動的人
   - 當地觀察者

   ❌ 錯誤：
   - 老李（退休工程師）
   - 村長王某
   - 某機構專家

---

2. 所有地點必須「模糊化」
   - 禁止真實溪流、山名、村名、專案名

   ✔ 正確：
   - 山區溪流
   - 某條河谷
   - 偏遠村落

   ❌ 錯誤：
   - 馬太鞍溪
   - 立霧溪
   - 東峻礦場

---

3. 所有時間與事件「去精確化」
   - 禁止年份、颱風名稱、政策名稱

   ✔ 正確：
   - 某次大雨之後
   - 多年前
   - 最近幾年

---

4. 禁止新聞語氣

❌ 不可：
- 解釋原因
- 引用數據
- 分析政策
- 做結論推導
- 評論對錯

✔ 只能：
- 看見
- 描述
- 切換畫面

---

5. 完全禁止：
- 真實事件還原
- 採訪語氣
- 專家觀點
- 社會評論
- 立場表述
- 因果分析

────────────────────
【鏡頭語言規則】

整體必須像「觀察型影像紀錄」：

畫面結構：

- 近景（手 / 水 / 土 / 光）
- 中景（人與空間）
- 遠景（山 / 村 / 天氣）
- 空白（停頓 / 無人 / 靜止）
- 切黑

允許使用：

（停頓）
（空鏡）
（風吹過）
（畫面靜止）
（無人）

👉 空白是敘事的一部分

────────────────────
【敘事限制】

- 不可解釋畫面意義
- 不可說「代表」
- 不可說「因此」
- 不可說「顯示」
- 不可總結
- 不可教學

────────────────────
【輸出格式（非常重要）】

只輸出 JSON：

{
  "title": "",
  "content": ""
}

────────────────────
【TITLE 規則】
- 12字內
- 像影像片名
- 不解釋內容

────────────────────
【CONTENT 規則】

- 使用 HTML
- 只允許 <p>
- 不可列表
- 每段像一個鏡頭
- 有節奏、有停頓

────────────────────
【長度】
300～600字

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
