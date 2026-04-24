def generate_article():
    """调用 DeepSeek API 生成文章内容，回傳 dict（包含 title, content, category, summary, key_points）"""
    if not DEEPSEEK_API_KEY:
        print("❌ 錯誤：DEEPSEEK_API_KEY 環境變數未設定")
        return None

    category = get_today_category()
    custom = get_custom_config()

    # 決定角色
    if custom["role"]:
        role_prompt = f"你是一位{custom['role']}，擅長撰寫有趣且專業的文章。"
        print(f"🎭 手動角色：{custom['role']}")
    else:
        role_prompt = DEFAULT_ROLES.get(category, "你是一位科普作家。")
        print(f"🎭 預設角色（{category}）")

    # 決定子主題
    if custom["topics"].get(category):
        subtopic = custom["topics"][category]
        print(f"🌱 手動主題：{subtopic}")
    else:
        subtopic = random.choice(SUB_TOPICS.get(category, ["一般主題"]))
        print(f"🌱 隨機主題：{subtopic}")

    # 決定寫作風格
    if custom["style"]:
        style = custom["style"]
        print(f"✍️ 手動風格：{style}")
    else:
        style = random.choice(DEFAULT_STYLES)
        print(f"✍️ 隨機風格：{style}")

    # 決定文章結構
    if custom["structure"]:
        structure = custom["structure"]
        print(f"📐 手動結構：{structure}")
    else:
        structure = random.choice(DEFAULT_STRUCTURES)
        print(f"📐 隨機結構：{structure}")

    # ✅ 強化版 Prompt
    prompt = f"""請寫一篇關於「{category}」的專業科普或生活文章。

今天的主題是：{subtopic}

寫作風格：{style}

文章結構：{structure}

【嚴格要求】
1. 文章長度：**至少 600 字，最多 900 字**（請確實遵守）
2. 內容必須包含：
   - 具體的實例或案例（至少 1 個）
   - 可操作的建議或步驟（至少 3 點）
   - 數據或研究發現（可合理推估，但要具體）
3. 結尾要有總結段落

【輸出格式】請以 JSON 格式輸出，包含以下欄位：
- title: 文章標題（12字以內，要吸引人）
- summary: 一句話總結（25字以內）
- key_points: 三個重點，格式為 ["重點一", "重點二", "重點三"]
- content: 文章內文（使用 HTML 格式，包含 <h2>、<p> 標籤）

【內容品質要求】
- 不要空泛的廢話，每段都要有實質內容
- 不要重複同樣的觀點
- 使用繁體中文，語氣自然流暢
- 結尾加上「🌿 蕨積 - 讓生活多一點綠」

【禁止事項】
- 禁止使用 Markdown 語法（不要用 **bold**、# 標題）
- 禁止輸出 JSON 以外的任何文字
- 禁止寫「總之」、「綜上所述」這類敷衍結尾
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    # ✅ 調整參數：降低溫度提高專注度，提高 max_tokens 給更多空間
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": role_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,      # 從 0.7 調低，讓 AI 更專注
        "max_tokens": 2500,      # 從 2000 調高，留更多空間
        "response_format": {"type": "json_object"}
    }

    print("🤖 正在呼叫 DeepSeek API 生成文章...")
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)  # timeout 延長到 90 秒
        response.raise_for_status()
        data = response.json()
        
        article_data = json.loads(data["choices"][0]["message"]["content"])
        
        title = article_data.get("title", "")
        summary = article_data.get("summary", "")
        key_points = article_data.get("key_points", [])
        content = article_data.get("content", "")
        
        # 清理可能殘留的 Markdown
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # 確保有標題
        if not title:
            title = f"{category}｜{subtopic[:20]}"
        
        # 確保 key_points 是列表且為 3 個
        if not isinstance(key_points, list):
            key_points = []
        while len(key_points) < 3:
            key_points.append("更多精彩內容請看內文")
        key_points = key_points[:3]
        
        # ✅ 品質檢查：文章長度
        content_text = re.sub(r'<[^>]+>', '', content)  # 移除 HTML 標籤
        word_count = len(content_text)
        
        print(f"✅ 文章生成成功：{title}")
        print(f"📂 類別：{category}")
        print(f"📏 文章長度：{word_count} 字")
        
        if word_count < 400:
            print(f"⚠️ 警告：文章太短（{word_count}字），建議檢查內容品質")
        elif word_count < 600:
            print(f"📌 提示：文章長度略低於目標（600-800），勉強接受")
        else:
            print(f"✨ 文章長度符合目標（600-800字）")
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "summary": summary,
            "key_points": key_points
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失敗：{e}")
        print(f"原始回應前 500 字：{data['choices'][0]['message']['content'][:500]}...")
        return None
    except requests.exceptions.Timeout:
        print("❌ API 呼叫超時（90秒），請稍後重試")
        return None
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None
