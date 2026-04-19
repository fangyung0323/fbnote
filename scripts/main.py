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
    """返回模板的 CSS 樣式"""
    return """/* ===== 共用樣式 ===== */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root {
      --ink: #1a1a14;
      --moss: #3d5a38;
      --fern: #5a7a4a;
      --sage: #8aab7a;
      --mist: #d4e4c8;
      --cream: #f5f0e8;
      --stone: #9a9080;
      --paper: #faf7f2;
    }
    body {
      font-family: 'Noto Sans TC', sans-serif;
      background: var(--paper);
      color: var(--ink);
      overflow-x: hidden;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    nav {
      position: fixed; top: 0; left: 0; right: 0; z-index: 100;
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 4vw; height: 72px;
      background: rgba(250,247,242,0.92);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(90,122,74,0.12);
    }
    nav.scrolled { box-shadow: 0 2px 24px rgba(61,90,56,0.10); }

    .logo { display: flex; align-items: center; gap: 10px; text-decoration: none; flex-shrink: 0; }
    .logo-mark { width: 38px; height: 38px; flex-shrink: 0; }
    .logo-mark img { width: 100%; height: 100%; object-fit: contain; display: block; }
    .logo-text {
      font-family: 'Noto Serif TC', serif;
      font-weight: 900;
      font-size: 1.35rem;
      color: var(--moss);
      letter-spacing: 0.05em;
      line-height: 1;
      white-space: nowrap;
    }
    .logo-text span {
      display: block;
      font-family: 'Cormorant Garamond', serif;
      font-weight: 300;
      font-size: 0.65rem;
      letter-spacing: 0.25em;
      color: var(--stone);
      margin-top: 2px;
    }

    .nav-links {
      display: flex;
      gap: 2rem;
      list-style: none;
      align-items: center;
      white-space: nowrap;
    }
    .nav-links li { position: relative; padding: 0 2px; }
    .nav-links a {
      font-family: 'Noto Sans TC', sans-serif;
      font-size: 0.82rem;
      font-weight: 400;
      letter-spacing: 0.1em;
      color: var(--ink);
      text-decoration: none;
      padding-bottom: 3px;
      opacity: 0.75;
      display: inline-block;
    }
    .nav-links a:hover { opacity: 1; color: var(--fern); }
    .nav-contact {
      padding: 8px 20px !important;
      border: 1px solid var(--fern) !important;
      border-radius: 2px;
      color: var(--fern) !important;
      opacity: 1 !important;
      margin-left: 0.5rem;
    }
    .nav-contact:hover { background: var(--fern); color: white !important; }

    .nav-links li .dropdown {
      display: none;
      position: absolute;
      top: calc(100% + 18px);
      left: 50%;
      transform: translateX(-50%);
      background: rgba(250,247,242,0.98);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(90,122,74,0.14);
      border-top: 2px solid var(--fern);
      box-shadow: 0 12px 40px rgba(61,90,56,0.12);
      min-width: 148px;
      list-style: none;
      padding: 8px 0;
      z-index: 300;
    }
    .nav-links li:hover .dropdown { display: block; }
    .nav-links li .dropdown::before {
      content: '';
      position: absolute;
      top: -7px;
      left: 50%;
      transform: translateX(-50%);
      border-left: 6px solid transparent;
      border-right: 6px solid transparent;
      border-bottom: 6px solid var(--fern);
    }
    .dropdown li a {
      display: block;
      padding: 10px 20px;
      font-size: 0.78rem;
      font-weight: 400;
      letter-spacing: 0.08em;
      color: var(--ink);
      opacity: 0.7;
      white-space: nowrap;
      text-decoration: none;
    }
    .dropdown li a:hover {
      opacity: 1;
      color: var(--fern);
      padding-left: 26px;
      background: rgba(90,122,74,0.04);
    }
    .dropdown li + li { border-top: 1px solid rgba(90,122,74,0.08); }

    .hamburger {
      display: none;
      flex-direction: column;
      justify-content: center;
      gap: 6px;
      width: 40px; height: 40px;
      cursor: pointer;
      background: none; border: none;
      flex-shrink: 0;
    }
    .hamburger span {
      display: block;
      width: 24px; height: 1.5px;
      background: var(--moss);
      transition: transform 0.2s ease;
    }
    .hamburger.open span:nth-child(1) { transform: translateY(7.5px) rotate(45deg); }
    .hamburger.open span:nth-child(2) { opacity: 0; }
    .hamburger.open span:nth-child(3) { transform: translateY(-7.5px) rotate(-45deg); }

    .mobile-menu {
      position: fixed; top: 72px; left: 0; right: 0; bottom: 0;
      background: #faf7f2;
      border-bottom: 1px solid rgba(90,122,74,0.15);
      padding: 0 6vw 40px;
      z-index: 99;
      overflow-y: auto;
      transform: translateX(100%);
      visibility: hidden;
      transition: transform 0.3s ease;
    }
    .mobile-menu.open { transform: translateX(0); visibility: visible; }
    .mobile-menu ul { list-style: none; }
    .mobile-menu > ul > li > a,
    .mobile-parent {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 0;
      font-family: 'Noto Serif TC', serif;
      font-weight: 600;
      font-size: 1rem;
      letter-spacing: 0.08em;
      color: var(--moss);
      text-decoration: none;
      border-bottom: 1px solid rgba(90,122,74,0.1);
      cursor: pointer;
    }
    .mobile-parent:hover { color: var(--fern); }
    .mobile-caret { display: inline-block; transition: transform 0.2s; }
    .mobile-caret.open { transform: rotate(180deg); }
    .mobile-sub {
      list-style: none;
      max-height: 0;
      overflow: hidden;
      transition: max-height 0.3s ease;
    }
    .mobile-sub.open { max-height: 200px; }
    .mobile-sub li a {
      display: block;
      padding: 11px 0 11px 16px;
      font-size: 0.85rem;
      color: var(--stone);
      text-decoration: none;
      border-bottom: 1px solid rgba(90,122,74,0.06);
      letter-spacing: 0.06em;
    }
    .mobile-sub li a:hover { color: var(--fern); }

    @media (max-width: 768px) {
      .nav-links { display: none; }
      .hamburger { display: flex; }
    }

    .content {
      flex: 1;
      padding-top: 92px;
      padding-bottom: 40px;
    }

    footer {
      border-top: 1px solid rgba(90,122,74,0.15);
      padding: 40px 4vw;
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--paper);
      margin-top: auto;
    }
    .footer-links {
      display: flex;
      gap: 24px;
      list-style: none;
    }
    .footer-links a {
      font-size: 0.75rem;
      color: var(--stone);
      text-decoration: none;
      letter-spacing: 0.08em;
      opacity: 0.7;
    }
    .footer-links a:hover {
      opacity: 1;
      color: var(--fern);
    }
    .footer-copy {
      font-size: 0.75rem;
      color: var(--stone);
      letter-spacing: 0.1em;
    }
    @media (max-width: 768px) {
      footer {
        flex-direction: column;
        gap: 20px;
        text-align: center;
      }
      .footer-links {
        justify-content: center;
        flex-wrap: wrap;
      }
    }"""

def get_footer_html():
    return """<footer>
    <ul class="footer-links">
      <li><a href="/shop.html">植物選品</a></li>
      <li><a href="/consult.html">綠色服務</a></li>
      <li><a href="/fbnote.html">蕨望筆記</a></li>
      <li><a href="/about.html">關於蕨積</a></li>
    </ul>
    <p class="footer-copy">© 2026 蕨積 FernBrom . All rights reserved.</p>
  </footer>"""

def get_nav_script():
    return r"""
document.addEventListener('DOMContentLoaded', function () {
  fetch('/nav.html')
    .then(response => response.text())
    .then(data => {
      let fixedData = data.replace(/href="(?!https?:\/\/|\/)([^"]+)"/g, 'href="/$1"');
      fixedData = fixedData.replace(/href="\/([^"]+)"/g, 'href="/$1"');
      document.getElementById('nav-placeholder').innerHTML = fixedData;
      initNav();
    })
    .catch(err => {
      console.error('無法載入導覽列:', err);
      document.getElementById('nav-placeholder').innerHTML = 
        '<nav style="background:var(--moss);color:white;padding:0 4vw;height:72px;display:flex;align-items:center;">' +
        '<span style="font-family:Noto Serif TC,serif;font-weight:900;">🌿 蕨積</span>' +
        '</nav>';
    });

  function initNav() {
    var btn = document.getElementById('hamburger');
    var menu = document.getElementById('mobileMenu');
    if (btn && menu) {
      btn.addEventListener('click', function () {
        btn.classList.toggle('open');
        menu.classList.toggle('open');
      });
      menu.querySelectorAll('.mobile-link').forEach(function (a) {
        a.addEventListener('click', function () {
          btn.classList.remove('open');
          menu.classList.remove('open');
        });
      });
    }
    if (menu) {
      menu.querySelectorAll('.mobile-parent').forEach(function (parent) {
        parent.addEventListener('click', function () {
          var id = parent.getAttribute('data-target');
          var sub = document.getElementById(id);
          var caretId = 'caret-' + id.replace('sub-', '');
          var caret = document.getElementById(caretId);
          var opening = !sub.classList.contains('open');
          menu.querySelectorAll('.mobile-sub').forEach(function (s) { s.classList.remove('open'); });
          menu.querySelectorAll('.mobile-caret').forEach(function (c) { c.classList.remove('open'); });
          if (opening) {
            sub.classList.add('open');
            if (caret) caret.classList.add('open');
          }
        });
      });
    }
    window.addEventListener('scroll', function () {
      var nav = document.getElementById('mainNav');
      if (nav) nav.classList.toggle('scrolled', window.scrollY > 20);
    });
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }
});
"""

# ==================== 文章生成 ====================
def generate_article():
    """调用 DeepSeek API 生成文章内容，回傳 dict 包含 title, content, category, summary, key_points"""
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

    # 組合提示詞（要求輸出 JSON）
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
4. 不要使用 Markdown 語法（不要用 **、##、*）
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
        
        # 解析 JSON 回應
        article_data = json.loads(data["choices"][0]["message"]["content"])
        
        title = article_data.get("title", "")
        summary = article_data.get("summary", "")
        key_points = article_data.get("key_points", [])
        content = article_data.get("content", "")
        
        # 清理可能殘留的 Markdown
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
    
    # 將 key_points 轉為 JSON 字串
    key_points_json = json.dumps(key_points, ensure_ascii=False)
    
    # 分類頁面對應表
    category_page_map = {
        "植物": "plant.html",
        "永續": "sustainability.html",
        "碳盤查": "carbon.html",
        "生活": "life.html"
    }
    category_page = category_page_map.get(category, "index.html")
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{summary}">
    <meta name="article-summary" content="{summary}">
    <meta name="article-keypoints" content='{key_points_json}'>
    <title>{title} - 蕨積每日文章</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600;900&family=Noto+Sans+TC:wght@300;400;500&family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>{get_template_styles()}
    .article-container {{
        max-width: 900px;
        margin: 0 auto;
        padding: 0 2rem;
    }}
    .article-category {{
        display: inline-block;
        background: {category_color};
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }}
    .article-title {{
        font-size: 2rem;
        color: var(--moss);
        margin-bottom: 0.5rem;
        font-family: 'Noto Serif TC', serif;
    }}
    .article-date {{
        color: var(--stone);
        margin-bottom: 2rem;
        font-size: 0.9rem;
    }}
    .article-content {{
        line-height: 1.8;
        font-size: 1rem;
    }}
    @media (max-width: 768px) {{
        .article-title {{ font-size: 1.5rem; }}
        .article-container {{ padding: 0 1rem; }}
    }}
    </style>
</head>
<body>
    <div id="nav-placeholder"></div>
    <main class="content">
        <div class="article-container">
            <div class="article-category">📌 {category}</div>
            <h1 class="article-title">{title}</h1>
            <div class="article-date">📅 {datetime.now().strftime("%Y年%m月%d日")}</div>
            <div class="article-content">{content_html}</div>
          
            <div class="footer">
                <br>每日一篇，與你一起成長<br><br>
                <div class="nav-links">
                    <a href="index.html">← 返回每日文章</a> &nbsp;|&nbsp;
                    <a href="{category_page}">← 返回{category}文章分類</a> &nbsp;|&nbsp;
                    <a href="../shop.html">🌱 植物選品</a> &nbsp;|&nbsp;
                    <a href="../consult.html">💚 綠色服務</a>
                </div>
            </div>
        </div>
    </main>
    {get_footer_html()}
    <script>{get_nav_script()}</script>
</body>
</html>"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"📄 文章已儲存：{filepath}")
    return filepath

# ==================== 索引頁面生成 ====================
def generate_daily_post_index(daily_post_dir):
    """產生 daily-post 目錄的索引頁面（外掛導覽列 + 分類篩選）"""
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

    archive_by_month = {}
    for article in past_articles:
        month_key = article["date"][:7]
        if month_key not in archive_by_month:
            archive_by_month[month_key] = []
        archive_by_month[month_key].append(article)

    past_list_html = ""
    for article in past_articles[:30]:
        cat_color = CATEGORY_COLORS.get(article["category"], "#6c757d")
        past_list_html += f"""
                        <li class="past-item" data-category="{article['category']}">
                            <span class="past-badge" style="background: {cat_color};">{article['category']}</span>
                            <a class="past-link" href="{article['filename']}">{article['title']}</a>
                            <div class="past-meta">📅 {article['date']}</div>
                        </li>"""

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

    latest_cat_color = CATEGORY_COLORS.get(latest['category'], "#6c757d")

    index_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>蕨積每日文章 - 植物・永續・碳盤查・生活</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600;900&family=Noto+Sans+TC:wght@300;400;500&family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>{get_template_styles()}
    .daily-container {{ max-width: 1200px; margin: 0 auto; padding: 0 2rem; }}
    .page-header {{ text-align: center; margin-bottom: 2rem; }}
    .page-header h1 {{ color: var(--moss); font-size: 2rem; font-family: 'Noto Serif TC', serif; }}
    .page-header p {{ color: var(--stone); margin-top: 0.5rem; }}
    
    .categories {{
        display: flex;
        justify-content: center;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 2rem;
    }}
    .category-btn {{
        padding: 0.5rem 1.5rem;
        border-radius: 30px;
        border: none;
        cursor: pointer;
        font-size: 0.9rem;
        font-weight: 500;
        transition: transform 0.2s;
        background: #e8e0d8;
        color: #4a5b4e;
    }}
    .category-btn:hover {{ transform: translateY(-2px); }}
    .category-btn.active {{ background: #4a7c59; color: white; }}
    
    .two-columns {{ display: flex; gap: 2rem; flex-wrap: wrap; }}
    .main-col {{ flex: 3; min-width: 250px; }}
    .sidebar-col {{ flex: 1; min-width: 200px; background: white; border-radius: 16px; padding: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05); height: fit-content; }}
    
    .latest-article {{
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }}
    .latest-category {{
        display: inline-block;
        background: {latest_cat_color};
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }}
    .latest-title {{ font-size: 1.8rem; color: var(--moss); margin-bottom: 0.5rem; }}
    .latest-date {{ color: var(--stone); margin-bottom: 1.5rem; font-size: 0.9rem; }}
    .latest-content {{ line-height: 1.8; }}
    .read-more {{ display: inline-block; margin-top: 1rem; color: var(--fern); text-decoration: none; font-weight: 500; }}
    
    .section-title {{ font-size: 1.2rem; color: var(--moss); border-bottom: 2px solid #e0d6cc; padding-bottom: 0.5rem; margin-bottom: 1rem; }}
    .past-list {{ list-style: none; }}
    .past-item {{ margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #f0e8e0; }}
    .past-link {{ font-size: 0.95rem; font-weight: 500; color: var(--fern); text-decoration: none; display: block; }}
    .past-link:hover {{ text-decoration: underline; }}
    .past-meta {{ font-size: 0.7rem; color: #aaa; margin-top: 0.25rem; }}
    .past-badge {{ display: inline-block; font-size: 0.65rem; padding: 0.1rem 0.5rem; border-radius: 12px; color: white; margin-right: 0.5rem; }}
    .archive-month {{ margin-bottom: 1rem; }}
    .archive-month-title {{ font-weight: 600; color: var(--moss); margin-bottom: 0.5rem; }}
    .archive-list {{ list-style: none; padding-left: 0.5rem; }}
    .archive-list li {{ margin-bottom: 0.3rem; }}
    .archive-list a {{ color: var(--stone); text-decoration: none; font-size: 0.85rem; }}
    .archive-list a:hover {{ color: var(--fern); text-decoration: underline; }}
    
    @media (max-width: 768px) {{
        .two-columns {{ flex-direction: column; }}
        .latest-title {{ font-size: 1.4rem; }}
        .daily-container {{ padding: 0 1rem; }}
    }}
    </style>
</head>
<body>
    <div id="nav-placeholder"></div>
    
    <main class="content">
        <div class="daily-container">
            <div class="page-header">
                <h1>🌿 蕨積每日文章</h1>
                <p>植物・永續・碳盤查・生活 — 每天一篇，與你一起成長</p>
            </div>
            
            <div class="categories">
                <a href="plant.html" class="category-btn" style="text-decoration: none;">🌿 植物</a>
                <a href="sustainability.html" class="category-btn" style="text-decoration: none;">♻️ 永續</a>
                <a href="carbon.html" class="category-btn" style="text-decoration: none;">📊 碳盤查</a>
                <a href="life.html" class="category-btn" style="text-decoration: none;">🏡 生活</a>
            </div>
            
            <div class="two-columns">
                <div class="main-col">
                    <div class="latest-article">
                        <div class="latest-category">📌 {latest['category']}</div>
                        <h1 class="latest-title">{latest['title']}</h1>
                        <div class="latest-date">📅 {latest['date']}</div>
                        <div class="latest-content">{latest['content']}</div>
                        <a href="{latest['filename']}" class="read-more">🔗 查看獨立頁面 →</a>
                    </div>
                    
                    <div class="section-title">📖 過往文章</div>
                    <ul class="past-list" id="pastList">
                        {past_list_html}
                    </ul>
                </div>
                
                <div class="sidebar-col">
                    <div class="section-title">📚 歷史歸檔</div>
                    {archive_html}
                </div>
            </div>
        </div>
    </main>
    
    {get_footer_html()}
    
    <script>
        {get_nav_script()}
    </script>
</body>
</html>"""

    index_path = os.path.join(daily_post_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"📑 已更新 daily-post/index.html (共 {len(articles)} 篇文章)")
    
    # ========== 新增: 為每個分類產生獨立頁面 ==========
    categories_list = ["植物", "永續", "碳盤查", "生活"]
    category_emojis = {"植物": "🌿", "永續": "♻️", "碳盤查": "📊", "生活": "🏡"}
    category_files = {"植物": "plant.html", "永續": "sustainability.html", "碳盤查": "carbon.html", "生活": "life.html"}
    
    for cat in categories_list:
        cat_articles = [a for a in articles if a["category"] == cat]
        
        cat_past_list_html = ""
        for article in cat_articles:
            cat_color = CATEGORY_COLORS.get(article["category"], "#6c757d")
            cat_past_list_html += f"""
                        <li class="past-item">
                            <span class="past-badge" style="background: {cat_color};">{article['category']}</span>
                            <a class="past-link" href="{article['filename']}">{article['title']}</a>
                            <div class="past-meta">📅 {article['date']}</div>
                        </li>"""
        
        if not cat_past_list_html:
            cat_past_list_html = '<li style="color: #aaa; text-align: center;">📭 暫無文章</li>'
        
        cat_latest = cat_articles[0] if cat_articles else None
        
        if cat_latest:
            cat_latest_cat_color = CATEGORY_COLORS.get(cat_latest['category'], "#6c757d")
            full_content = cat_latest.get('content', '')
            plain_content = re.sub(r'<[^>]+>', '', full_content)
            preview_length = min(300, len(plain_content))
            preview_content = plain_content[:preview_length]
            if len(plain_content) > preview_length:
                preview_content += "..."
            
            cat_latest_html = f"""
                    <div class="latest-article">
                        <div class="latest-category" style="background: {cat_latest_cat_color};">📌 {cat_latest['category']}</div>
                        <h1 class="latest-title">{cat_latest['title']}</h1>
                        <div class="latest-date">📅 {cat_latest['date']}</div>
                        <div class="latest-content">{preview_content}</div>
                        <a href="{cat_latest['filename']}" class="read-more">🔗 閱讀全文 →</a>
                    </div>"""
        else:
            cat_latest_html = '<div style="text-align:center;padding:40px;color:var(--stone);">📭 此分類尚無文章</div>'
        
        cat_page_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category_emojis[cat]} {cat}文章 - 蕨積每日文章</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600;900&family=Noto+Sans+TC:wght@300;400;500&family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>{get_template_styles()}
    .daily-container {{ max-width: 1200px; margin: 0 auto; padding: 0 2rem; }}
    .page-header {{ text-align: center; margin-bottom: 2rem; }}
    .page-header h1 {{ color: var(--moss); font-size: 2rem; font-family: 'Noto Serif TC', serif; }}
    .page-header p {{ color: var(--stone); margin-top: 0.5rem; }}
    
    .two-columns {{ display: flex; gap: 2rem; flex-wrap: wrap; }}
    .main-col {{ flex: 3; min-width: 250px; }}
    
    .latest-article {{
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }}
    .latest-category {{
        display: inline-block;
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }}
    .latest-title {{ font-size: 1.8rem; color: var(--moss); margin-bottom: 0.5rem; }}
    .latest-date {{ color: var(--stone); margin-bottom: 1.5rem; font-size: 0.9rem; }}
    .latest-content {{ line-height: 1.8; }}
    .read-more {{ display: inline-block; margin-top: 1rem; color: var(--fern); text-decoration: none; font-weight: 500; }}
    
    .section-title {{ font-size: 1.2rem; color: var(--moss); border-bottom: 2px solid #e0d6cc; padding-bottom: 0.5rem; margin-bottom: 1rem; }}
    .past-list {{ list-style: none; }}
    .past-item {{ margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #f0e8e0; }}
    .past-link {{ font-size: 0.95rem; font-weight: 500; color: var(--fern); text-decoration: none; display: block; }}
    .past-link:hover {{ text-decoration: underline; }}
    .past-meta {{ font-size: 0.7rem; color: #aaa; margin-top: 0.25rem; }}
    .past-badge {{ display: inline-block; font-size: 0.65rem; padding: 0.1rem 0.5rem; border-radius: 12px; color: white; margin-right: 0.5rem; }}
    
    @media (max-width: 768px) {{
        .two-columns {{ flex-direction: column; }}
        .latest-title {{ font-size: 1.4rem; }}
        .daily-container {{ padding: 0 1rem; }}
    }}
    </style>
</head>
<body>
    <div id="nav-placeholder"></div>
    
    <main class="content">
        <div class="daily-container">
            <div class="page-header">
                <h1>{category_emojis[cat]} {cat}文章</h1>
                <p>蕨積每日文章 - {cat}分類精選</p>
            </div>
            
            <div class="two-columns">
                <div class="main-col">
                    {cat_latest_html}
                    
                    <div class="section-title">📖 過往文章</div>
                    <ul class="past-list">
                        {cat_past_list_html}
                    </ul>
                </div>
            </div>
        </div>
    </main>
    
    {get_footer_html()}
    
    <script>
        {get_nav_script()}
    </script>
</body>
</html>"""
        
        cat_filepath = os.path.join(daily_post_dir, category_files[cat])
        with open(cat_filepath, "w", encoding="utf-8") as f:
            f.write(cat_page_html)
        print(f"📁 已產生分類頁面：{category_files[cat]}")
  
# ==================== 推送 ====================
def commit_and_push_to_website():
    print("=" * 50)
    print("開始推送到網站倉庫...")
    username = os.getenv("GITHUB_USERNAME", "isa930323-jpg")
    token = os.getenv("GH_TOKEN")
    repo_name = os.getenv("WEBSITE_REPO_NAME", "fb")
    print(f"📌 用戶名: {username}")
    print(f"📌 倉庫名: {repo_name}")
    if not token:
        print("❌ 錯誤：GH_TOKEN 環境變數未設定")
        return
    repo_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    with tempfile.TemporaryDirectory() as tmpdir:
        print("📥 正在 clone 網站倉庫...")
        r = subprocess.run(["git", "clone", repo_url, "website"], cwd=tmpdir, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"❌ Clone 失敗: {r.stderr}")
            return
        website_dir = os.path.join(tmpdir, "website")
        daily_dir = os.path.join(website_dir, "daily-post")
        os.makedirs(daily_dir, exist_ok=True)
        if os.path.exists("articles"):
            for f in os.listdir("articles"):
                if f.endswith(".html"):
                    shutil.copy2(os.path.join("articles", f), os.path.join(daily_dir, f))
        generate_daily_post_index(daily_dir)
        subprocess.run(["git", "config", "user.name", "jueji-bot"], cwd=website_dir, check=False)
        subprocess.run(["git", "config", "user.email", "bot@jueji.com"], cwd=website_dir, check=False)
        subprocess.run(["git", "add", "daily-post/"], cwd=website_dir, check=True)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=website_dir, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", f"每日發文 {datetime.now().strftime('%Y-%m-%d')}"], cwd=website_dir, check=False)
            push = subprocess.run(["git", "push", "origin", "main"], cwd=website_dir, capture_output=True, text=True)
            if push.returncode == 0:
                print("✅ 成功推送到網站倉庫")
            else:
                print(f"❌ 推送失敗: {push.stderr}")
        else:
            print("📭 沒有新的變更需要推送")

# ==================== 主程式 ====================
def main():
    print("=" * 50)
    print("🌿 蕨積每日發文機器人啟動")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
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
