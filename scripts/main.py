#!/usr/bin/env python3
"""
每日自動發文機器人
- 四大類別輪換：植物、永續、碳盤查、生活
- 支援手動觸發時透過環境變數覆蓋預設設定（AI角色、風格、結構、各類別主題）
- 預設主題從內建庫中隨機選擇
- 文章保存為 HTML（套用官網模板）
- 推送到網站倉庫的 daily-post 目錄
- 自動生成索引頁面（外掛導覽列 + 分類篩選）
"""

import os
import sys
import random
import subprocess
import shutil
import tempfile
import re
import json
from datetime import datetime
import requests

# 導入共用工具函數
from utils import check_today_article_exists

# ==================== 配置 ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

CATEGORIES = ["植物", "永續", "碳盤查", "生活"]
CATEGORY_COLORS = {
    "植物": "#4a7c59",
    "永續": "#2c7a4d",
    "碳盤查": "#1e6f5c",
    "生活": "#b88b4a"
}

# ==================== 子主題庫（預設） ====================
SUB_TOPICS = {
    "植物": [
        "植生牆入門指南：打造你的第一面垂直花園",
        "室內植物養護秘訣：讓你的綠朋友活得更健康",
        "植生牆養護全攻略：修剪、施肥、病蟲害防治",
        "從零開始：植生牆的結構、防水、排水規劃",
        "植物如何悄悄改善你的室內空氣品質",
        "辦公室植生牆：提升工作效率的綠色解方",
        "植生牆的燈光設計：晚上也能欣賞的綠牆美學",
        "植物療癒力：為什麼看著植物會感到放鬆",
        "台灣原生植物之美：認識身邊的綠色鄰居",
        "植物與兒童教育：讓孩子從自然中學習",
        "辦公室植物推薦：提升工作效率的綠色夥伴"
    ],
    "永續": [
        "零浪費生活入門：從今天開始減少垃圾",
        "減塑小撇步：塑膠袋之外的選擇",
        "永續消費指南：買得更少，買得更好",
        "如何打造低碳生活：日常減碳行動",
        "二手衣物的第二人生：循環經濟入門",
        "綠色能源在家應用：太陽能、風力怎麼用",
        "永續飲食：從餐桌開始改變世界",
        "企業永續案例：那些做對事的大公司",
        "環保旅遊怎麼玩：低碳出遊指南",
        "永續投資入門：用錢投票給更好的未來"
    ],
    "碳盤查": [
        "什麼是碳足跡？從一杯咖啡開始算起",
        "企業如何開始碳盤查：步驟與準備",
        "個人碳足跡計算：算出你的隱形碳排放",
        "碳中和是什麼？真的能讓排放歸零嗎",
        "淨零排放趨勢：企業與國家的新目標",
        "碳權交易基礎知識：買賣排放的市場",
        "生活中的減碳行動：省電、省水、省碳",
        "碳盤查常見問題：一次搞懂所有疑問",
        "國際碳關稅對台灣的影響與因應",
        "中小企業碳管理入門：從哪裡開始"
    ],
    "生活": [
        "斷捨離實踐指南：告別雜物，迎接清爽",
        "正念練習入門：專注當下的簡單方法",
        "居家收納美學：小空間也能住得舒適",
        "簡單生活哲學：少即是多的幸福",
        "生活儀式感提案：讓平凡日子變特別",
        "慢生活：在快節奏中找回自己",
        "數字排毒：如何減少手機使用時間",
        "手作療癒時光：用雙手創造快樂",
        "與自己獨處的藝術：享受一個人的時光",
        "創造幸福小習慣：每天一點點正向改變"
    ]
}

# ==================== 預設角色（依類別） ====================
DEFAULT_ROLES = {
    "植物": "你是一位植物學科普作家，擅長撰寫有趣且專業的植物文章。",
    "永續": "你是一位環境永續專家，擅長用淺顯易懂的方式講解永續議題。",
    "碳盤查": "你是一位碳管理顧問，擅長解釋碳盤查與氣候變遷相關知識。",
    "生活": "你是一位生活風格作家，擅長分享質感生活與心靈成長的內容。"
}

# ==================== 預設風格（隨機） ====================
DEFAULT_STYLES = [
    "輕鬆活潑，像朋友聊天",
    "專業科普，有數據支持",
    "故事敘述，從故事開始",
    "問答形式，自問自答",
    "清單體，條列呈現",
    "對比分析，比較觀點",
    "日記體，個人經驗"
]

# ==================== 預設結構（隨機） ====================
DEFAULT_STRUCTURES = [
    "開門見山：開頭直接點出主題和觀點",
    "故事引入：用小故事或案例開場",
    "問題解決：提出問題 → 分析 → 解答",
    "條列清單：用數字或項目符號整理",
    "對比分析：A vs B，比較異同"
]

# ==================== 輔助函數 ====================
def get_today_category():
    """根據手動觸發或日期決定類別"""
    manual = os.getenv("MANUAL_CATEGORY")
    if manual and manual != "自動（依日期輪換）" and manual in CATEGORIES:
        print(f"📌 手動選擇類別：{manual}")
        return manual
    day_of_year = datetime.now().timetuple().tm_yday
    category_index = (day_of_year - 1) % len(CATEGORIES)
    return CATEGORIES[category_index]

def get_custom_config():
    """從環境變數讀取使用者自訂設定（手動觸發時使用）"""
    return {
        "role": os.getenv("AI_ROLE"),
        "style": os.getenv("WRITING_STYLE"),
        "structure": os.getenv("ARTICLE_STRUCTURE"),
        "topics": {
            "植物": os.getenv("PLANT_TOPIC"),
            "永續": os.getenv("SUSTAIN_TOPIC"),
            "碳盤查": os.getenv("CARBON_TOPIC"),
            "生活": os.getenv("LIFE_TOPIC")
        }
    }

# ==================== 模板輔助函數 ====================
def get_template_styles():
    """返回模板的 CSS 樣式（內容太長，省略，請保留你原有的）"""
    return """/* 你的 CSS 內容 */"""

def get_footer_html():
    return """<footer>...</footer>"""

def get_nav_script():
    return """// 你的 JavaScript 內容"""

# ==================== 文章生成 ====================
def generate_article():
    """调用 DeepSeek API 生成文章内容"""
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

    prompt = f"""請寫一篇關於「{category}」的科普或生活文章。

今天的主題是：{subtopic}

寫作風格：{style}

文章結構：{structure}

【重要】請以 JSON 格式輸出，包含以下欄位：
- title: 文章標題（15字以內）
- summary: 一句話總結（30字以內）
- key_points: 三個重點，格式為 ["重點一", "重點二", "重點三"]
- content: 文章內文（使用 HTML 格式，包含 <h2>、<p> 標籤）

要求：
1. 文章長度約 500-800 字
2. 語言使用繁體中文
3. 結尾加上「🌿 蕨積 - 讓生活多一點綠」
4. 不要使用 Markdown 語法
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
        "response_format": {"type": "json_object"}
    }

    print("🤖 正在呼叫 DeepSeek API 生成文章...")
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        article_data = json.loads(data["choices"][0]["message"]["content"])
        
        title = article_data.get("title", "")
        summary = article_data.get("summary", "")
        key_points = article_data.get("key_points", [])
        content = article_data.get("content", "")
        
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        if not title:
            title = f"{category}｜{subtopic[:20]}"

        print(f"✅ 文章生成成功：{title}")
        print(f"📂 類別：{category}")
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "summary": summary,
            "key_points": key_points
        }
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None

# ==================== 儲存文章 ====================
def save_article_as_html(title, content, category, summary, key_points, output_dir="articles"):
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = title.replace(" ", "-").replace("/", "-").replace("?", "").replace("！", "")[:50]
    safe_title = re.sub(r'^(標題|Title)[:：]\s*', '', safe_title)
    filename = f"{date_str}-{safe_title}.html"
    filepath = os.path.join(output_dir, filename)
    category_color = CATEGORY_COLORS.get(category, "#4a7c59")
    content_html = content.replace("\n", "<br>")
    key_points_json = json.dumps(key_points, ensure_ascii=False)
    
    category_page_map = {
        "植物": "plant.html",
        "永續": "sustainability.html",
        "碳盤查": "carbon.html",
        "生活": "life.html"
    }
    category_page = category_page_map.get(category, "index.html")
    
    # 這裡放你的 HTML 模板（省略，請保留你原有的）
    html_content = f"""<!DOCTYPE html>..."""  # 你的完整 HTML 模板
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"📄 文章已儲存：{filepath}")
    return filepath

# ==================== 索引頁面生成 ====================
def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面"""
    # 這裡放你原有的 generate_daily_post_index 函數內容
    pass

# ==================== 推送 ====================
def commit_and_push_to_website():
    """推送到網站倉庫"""
    # 這裡放你原有的 commit_and_push_to_website 函數內容
    pass

# ==================== 主程式（唯一的一個） ====================
def main():
    print("=" * 50)
    print("🌿 蕨積每日發文機器人啟動")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ========== 防重複檢查 ==========
    if check_today_article_exists():
        print("❌ 今天已經有文章了，跳過本次發文（避免重複）")
        print("💡 如需強制發文，請手動刪除今天的文章後再執行")
        return
    # ================================
    
    article = generate_article()
    if not article or not article.get("title"):
        print("❌ 文章生成失敗")
        sys.exit(1)
    
    title = article.get("title")
    content = article.get("content")
    cat = article.get("category")
    summary = article.get("summary", "")
    key_points = article.get("key_points", [])
    
    save_article_as_html(title, content, cat, summary, key_points)
    commit_and_push_to_website()
    print("🎉 每日發文流程完成")

if __name__ == "__main__":
    main()
