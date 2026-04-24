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

    # ✅ 修改 prompt：明確要求 JSON 格式，包含 summary 和 key_points
    prompt = f"""請寫一篇關於「{category}」的科普或生活文章。

今天的主題是：{subtopic}

寫作風格：{style}

文章結構：{structure}

【重要】請以 JSON 格式輸出，包含以下欄位：
- title: 文章標題（15字以內，吸引人）
- summary: 一句話總結（30字以內，讓人想點進來）
- key_points: 三個重點，格式為 ["重點一", "重點二", "重點三"]
- content: 文章內文（使用 HTML 格式，包含 <h2>、<p> 標籤）

要求：
1. 文章長度約 500-800 字
2. 語言使用繁體中文
3. 結尾加上「🌿 蕨積 - 讓生活多一點綠」
4. 不要使用 Markdown 語法（不要用 **bold**、# 標題）
5. 不要輸出 JSON 以外的任何文字
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
        "temperature": 0.7,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}  # ✅ 強制 JSON 輸出
    }

    print("🤖 正在呼叫 DeepSeek API 生成文章...")
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # ✅ 解析 JSON
        article_data = json.loads(data["choices"][0]["message"]["content"])
        
        title = article_data.get("title", "")
        summary = article_data.get("summary", "")
        key_points = article_data.get("key_points", [])
        content = article_data.get("content", "")
        
        # ✅ 清理可能殘留的 Markdown
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # 確保有標題
        if not title:
            title = f"{category}｜{subtopic[:20]}"
        
        # 確保 key_points 是列表
        if not isinstance(key_points, list):
            key_points = []
        
        print(f"✅ 文章生成成功：{title}")
        print(f"📂 類別：{category}")
        print(f"📝 摘要：{summary[:50]}..." if summary else "⚠️ 無摘要")
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "summary": summary,
            "key_points": key_points
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失敗：{e}")
        print(f"原始回應：{data['choices'][0]['message']['content'][:200]}...")
        return None
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None
