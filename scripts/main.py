#!/usr/bin/env python3
"""
每日自動發文機器人
- 四大類別輪換：植物、永續、碳盤查、生活
- 支援手動觸發時透過環境變數覆蓋預設設定（AI角色、風格、結構、各類別主題）
- 預設主題從內建庫中隨機選擇（當沒有新聞資料時）
- **優先從爬蟲新聞 JSON 讀取真實新聞作為主題來源**
- **要求 AI 生成 70% 以上原創觀點，新聞僅作為切入點**
- 文章保存為 HTML（套用官網模板）
- 推送到網站倉庫的 daily-post 目錄
- 自動生成索引頁面（外掛導覽列 + 分類篩選 + 即時搜尋）
"""

import os
import sys
import random
import subprocess
import shutil
import tempfile
import re
import json
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Optional

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

# ==================== 爬蟲新聞資料路徑 ====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # fbnote 根目錄
NEWS_DATA_DIR = os.path.join(BASE_DIR, "news-data")

# 類別名稱對應（Post-Daily 類別 → 爬蟲 JSON 檔案）
CATEGORY_NEWS_FILE = {
    "植物": "green_wall.json",
    "永續": "esg.json",
    "碳盤查": "carbon.json",
    "生活": "life.json"
}

# ==================== 子主題庫（預設，當沒有新聞資料時使用） ====================
SUB_TOPICS = {
    "植物": [
        "植生牆入門指南：打造你的第一面垂直花園",
        "室內植物養護秘訣：讓你的綠朋友活得更健康",
        "從零開始：植生牆的結構、防水、排水規劃",
        "植物如何悄悄改善你的室內空氣品質",
        "辦公室植生牆：提升工作效率的綠色解方",
        "植物療癒力：為什麼看著植物會感到放鬆",
        "台灣原生植物之美：認識身邊的綠色鄰居",
        "植物與兒童教育：讓孩子從自然中學習",
        "植生牆的結構設計：骨架、防水、排水一次搞懂",
        "植生牆植物怎麼選？耐陰、好養、漂亮的推薦清單",
        "植生牆養護全攻略：澆水、修剪、施肥、病蟲害",
        "室內植生牆 vs 戶外植生牆：設計重點大不同",
        "小空間大改造：陽台植生牆這樣做",
        "辦公室植生牆：提升工作效率與空氣品質",
        "植生牆的自動澆灌系統：懶人也能養得漂亮",
        "植生牆的燈光設計：白天晚上都美的關鍵",
        "植生牆常見失敗原因與解決方案",
        "預算有限怎麼做？低成本植生牆DIY教學",
        "植生牆如何影響室內溫度和濕度？",
        "商業空間植生牆：餐廳、旅店、店面的吸睛利器",
        "植生牆的永續價值：綠化、節能、減碳一次滿足",
        "台灣適合植生牆的原生植物推薦",
        "植生牆的維護成本分析：長期持有值得嗎？",
        "從零開始：植生牆施工流程完整解析",
        "植生牆 vs 傳統盆栽：優缺點比較",
        "植生牆如何幫助建築降溫？實測數據分享",
        "打造會呼吸的家：植生牆讓室內空氣更清新",
        "辦公室植物推薦：提升工作效率的綠色夥伴",
        "居家植生牆設計：客廳、陽台、臥室怎麼擺",
        "植物殺手救星：最難養死的10種室內植物",
        "水耕植物入門：不用土也能種出綠意",
        "多肉植物照顧大全：澆水、日照、換盆一次懂",
        "植物與風水：室內綠化如何帶來好運",
        "租屋族必看：不傷牆面的植生牆解決方案"
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
        "永續投資入門：用錢投票給更好的未來",
        "SDGs是什麼？聯合國永續發展目標懶人包",
        "B型企業認證：對社會有貢獻的公司",
        "永續時尚：買衣服也能愛地球",
        "共享經濟：創造更多價值的消費模式",
        "都市永續轉型：綠色交通與智慧城市"
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
        "中小企業碳管理入門：從哪裡開始",
        "ISO 14064 碳盤查標準白話文解釋",
        "範疇一、二、三：企業碳排的三種分類",
        "碳抵換專案：花錢就能解決碳排放嗎",
        "科學基礎減碳目標 SBTi 是什麼",
        "RE100：企業使用100%再生能源的承諾"
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
        "創造幸福小習慣：每天一點點正向改變",
        "晨間習慣養成：如何擁有一個美好的早晨",
        "極簡主義入門：留下真正重要的東西",
        "居家改造 DIY：小預算打造舒適空間",
        "有效時間管理：擺脫拖延症的方法",
        "情緒覺察練習：更好理解自己"
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
    "日記體，個人經驗",
    "第一人稱觀點，分享個人想法",
    "案例分析，從具體例子出發"
]

# ==================== 預設結構（隨機） ====================
DEFAULT_STRUCTURES = [
    "開門見山：開頭直接點出主題和觀點",
    "故事引入：用小故事或案例開場",
    "問題解決：提出問題 → 分析 → 解答",
    "條列清單：用數字或項目符號整理",
    "對比分析：A vs B，比較異同",
    "觀點論述：提出觀點 → 論證 → 結論"
]

# ==================== 從爬蟲 JSON 讀取新聞 ====================
def load_news_from_json(category: str) -> Optional[List[Dict]]:
    """
    從爬蟲產生的 JSON 檔案讀取指定類別的新聞
    回傳格式：[{"title": "...", "source": "...", "date": "...", "summary": "...", "content": "..."}]
    """
    filename = CATEGORY_NEWS_FILE.get(category)
    if not filename:
        return None
    
    filepath = os.path.join(NEWS_DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"📭 新聞檔案不存在: {filepath}")
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            news_list = json.load(f)
        
        if not news_list:
            print(f"📭 {category} 分類暫無新聞資料")
            return None
        
        print(f"📰 成功載入 {category} 分類新聞：共 {len(news_list)} 則")
        return news_list
        
    except Exception as e:
        print(f"⚠️ 讀取新聞 JSON 失敗 ({category}): {e}")
        return None


def get_news_based_topic(category: str) -> Optional[Dict]:
    """
    從新聞中隨機挑選一則作為主題
    回傳格式：{"topic": "新聞標題", "news_context": "格式化後的文字", "source": "...", "date": "..."}
    """
    news_list = load_news_from_json(category)
    if not news_list:
        return None
    
    # 隨機選擇一則新聞
    selected = random.choice(news_list)
    
    # 格式化新聞內容供 AI 參考（精簡版，避免 AI 直接複製）
    news_context = f"""
【新聞摘要】
標題：{selected.get('title', '無標題')}
來源：{selected.get('source', '未知來源')}
日期：{selected.get('date', '日期不詳')}
核心內容：{selected.get('summary', '無摘要')[:200]}
{'重點節錄：' + selected.get('content', '')[:300] + '...' if selected.get('content') else ''}
"""
    
    return {
        "topic": selected.get('title', ''),
        "news_context": news_context,
        "source": selected.get('source', ''),
        "date": selected.get('date', ''),
        "url": selected.get('url', '')
    }


def get_all_news_context(category: str, max_items: int = 3) -> Optional[str]:
    """
    獲取該分類的所有新聞（取最新 N 則），格式化成完整的參考資料
    """
    news_list = load_news_from_json(category)
    if not news_list:
        return None
    
    # 按日期排序（最新的在前）
    sorted_news = sorted(news_list, key=lambda x: x.get('date', ''), reverse=True)
    top_news = sorted_news[:max_items]
    
    context_parts = ["以下是與本主題相關的最新新聞資料，請參考這些真實新聞來撰寫文章：\n"]
    
    for i, news in enumerate(top_news, 1):
        context_parts.append(f"""
【新聞 {i}】
標題：{news.get('title', '無標題')}
來源：{news.get('source', '未知來源')}
日期：{news.get('date', '日期不詳')}
摘要：{news.get('summary', '無摘要')}
{'原文摘要：' + news.get('content', '')[:300] + '...' if news.get('content') else ''}
""")
    
    return "\n".join(context_parts)


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
document.addEventListener('DOMContentLoaded', function() {
  fetch('../nav.html')
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
      btn.addEventListener('click', function() {
        btn.classList.toggle('open');
        menu.classList.toggle('open');
      });
      
      menu.querySelectorAll('.mobile-link').forEach(function(a) {
        a.addEventListener('click', function() {
          btn.classList.remove('open');
          menu.classList.remove('open');
        });
      });
    }
    
    if (menu) {
      menu.querySelectorAll('.mobile-parent').forEach(function(parent) {
        parent.addEventListener('click', function() {
          var id = parent.getAttribute('data-target');
          var sub = document.getElementById(id);
          var caret = parent.querySelector('.mobile-caret');
          var opening = !sub.classList.contains('open');
          
          menu.querySelectorAll('.mobile-sub').forEach(function(s) { 
            s.classList.remove('open'); 
          });
          menu.querySelectorAll('.mobile-caret').forEach(function(c) { 
            c.classList.remove('open'); 
          });
          
          if (opening) {
            sub.classList.add('open');
            if (caret) caret.classList.add('open');
          }
        });
      });
    }
    
    window.addEventListener('scroll', function() {
      var nav = document.getElementById('mainNav');
      if (nav) nav.classList.toggle('scrolled', window.scrollY > 20);
    });
    
    if (typeof lucide !== 'undefined') lucide.createIcons();
  });
}
"""

# ==================== 文章生成（核心：70% 原創觀點） ====================
def generate_article():
    """调用 DeepSeek API 生成文章内容，回傳 dict
    要求：70% 以上原創觀點，新聞僅作為切入點和案例參考
    """
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

    # ==================== 從新聞讀取主題 ====================
    news_data = None
    subtopic = None
    news_context = None
    
    # 檢查是否有手動指定主題（手動模式優先）
    if custom["topics"].get(category):
        subtopic = custom["topics"][category]
        print(f"🌱 手動主題：{subtopic}")
    else:
        # 嘗試從爬蟲新聞讀取
        news_data = get_news_based_topic(category)
        
        if news_data:
            # 有新聞資料，使用新聞標題作為切入點
            subtopic = news_data["topic"]
            news_context = news_data["news_context"]
            print(f"📰 新聞切入點：{subtopic}")
            print(f"📰 新聞來源：{news_data.get('source', '未知')} ({news_data.get('date', '日期不詳')})")
        else:
            # 沒有新聞資料，回退到內建主題庫
            subtopic = random.choice(SUB_TOPICS.get(category, ["一般主題"]))
            print(f"🌱 隨機主題（內建）：{subtopic}")

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

    # ==================== 建構 Prompt（70% 原創觀點版本） ====================
    
    if news_context:
        # 有新聞資料時：新聞僅作為 30% 的參考，要求 70% 原創
        news_section = f"""
【📰 參考新聞（僅作為切入點和案例，請勿照抄）】
{news_context}

【⚠️ 核心要求：原創觀點優先】
這則新聞只是一個「起點」或「案例參考」，請你不要只是複述新聞內容。

請依照以下比例撰寫文章：
- 🟢 30%：引用新聞中的具體資訊（數據、案例、政策內容）作為佐證
- 🟡 70%：你的原創觀點、深度分析、延伸思考、實務建議

具體做法：
1. **開頭（15%）**：用新聞事件作為引言，但提出你的觀察角度
2. **分析（40%）**：從新聞延伸出去的專業分析，包含：
   - 這個現象背後的原因是什麼？
   - 對讀者（個人/企業）有什麼影響？
   - 你預測未來的發展趨勢？
3. **觀點（30%）**：你的獨特見解和立場
   - 支持或反對？為什麼？
   - 有什麼更好的做法？
4. **行動建議（15%）**：給讀者的具體建議

✅ 好的例子：
   - 「從這則新聞可以看出，台灣的植生牆政策正在轉向⋯⋯我認為接下來應該注意三個方向⋯⋯」
   - 「新聞中提到每坪補助3000元，但真正的問題在於後續維護成本。根據我的觀察⋯⋯」

❌ 壞的例子（太像新聞稿）：
   - 「台北市都發局宣布，將補助建築物設置植生牆⋯⋯」
   - 「根據報導，這項政策將於明年實施⋯⋯」
"""
    else:
        # 沒有新聞資料時：完全依賴 AI 知識，100% 原創
        news_section = f"""
【寫作說明】
目前無特定新聞參考資料，請完全基於你的專業知識撰寫。

【要求】
- 請寫出具有原創觀點和深度的內容
- 不要使用「根據新聞報導」、「近期研究顯示」這類空泛引用
- 用自己的話解釋概念，提出獨特見解
"""

    prompt = f"""請寫一篇關於「{category}」的專業科普或生活文章。

{news_section}

今天的主題 / 切入點是：{subtopic}

寫作風格：{style}

文章結構：{structure}

【重要】請以 JSON 格式輸出，包含以下欄位：
- title: 文章標題（15字以內，吸引人，最好能體現你的觀點）
- summary: 一句話總結（30字以內，讓人想點進來）
- key_points: 三個重點，格式為 ["重點一", "重點二", "重點三"]
- content: 文章內文（使用 HTML 格式，包含 <h2>、<p> 標籤）

【文章長度】500-800 字
【語言】繁體中文
【結尾】加上「🌿 蕨積 - 讓生活多一點綠」

【禁止事項】
1. 不要使用 Markdown 語法（不要用 **bold**、# 標題）
2. 不要寫「根據新聞報導」、「據了解」、「相關單位表示」這類新聞稿語言
3. 不要只是改寫新聞內容
4. 不要輸出 JSON 以外的任何文字

【原創性檢查】
寫完後請自我檢查：這篇文章是否有 70% 以上的內容是你的觀點和分析？
如果沒有，請重新思考角度再寫。
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
        "temperature": 0.8,  # 稍微提高溫度，增加原創性
        "max_tokens": 2500,
        "response_format": {"type": "json_object"}
    }

    print("🤖 正在呼叫 DeepSeek API 生成文章（要求 70% 原創觀點）...")
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        data = response.json()
        
        article_data = json.loads(data["choices"][0]["message"]["content"])
        
        title = article_data.get("title", "")
        summary = article_data.get("summary", "")
        key_points = article_data.get("key_points", [])
        content = article_data.get("content", "")
        
        # 清理 Markdown
        content = re.sub(r'\*\*(.+?)\*\*', r'\1', content)
        content = re.sub(r'\*(.+?)\*', r'\1', content)
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        if not title:
            title = f"{category}｜{subtopic[:20]}"
        
        if not isinstance(key_points, list):
            key_points = []

        print(f"✅ 文章生成成功：{title}")
        print(f"📂 類別：{category}")
        if news_data:
            print(f"📰 參考新聞：{news_data.get('source', '未知')}")
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "summary": summary,
            "key_points": key_points,
            "news_used": news_data is not None
        }
    except Exception as e:
        print(f"❌ API 呼叫失敗：{e}")
        return None

# ==================== 儲存文章 ====================
from bs4 import BeautifulSoup

# 内部链接映射表 (关键词 -> 目标URL，从 daily-post/ 出发的相对路径)
LINK_MAP = {
    "植物": "../shop.html",
    "購買": "../shop.html",
    "植生牆": "../greenwall.html",
    "垂直綠化": "../greenwall.html",
    "碳盤查": "../consult.html",
    "碳足跡": "../consult.html",
    "ESG": "../consulting.html",
    "永續": "../consulting.html",
    "生活": "../lifestyle.html",
    "零浪費": "../lifestyle.html",
    "減塑": "../lifestyle.html",
}

def add_internal_links(html_content):
    """在文章内容的文本节点中添加内部链接（相对路径）"""
    if not html_content:
        return html_content
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 按关键词长度降序排序（避免短词先替换影响长词）
    keywords = sorted(LINK_MAP.keys(), key=len, reverse=True)
    
    for text_node in soup.find_all(string=True):
        # 跳过 script、style 标签内以及已经是链接内部的文本
        parent = text_node.parent
        if parent.name in ['script', 'style', 'a']:
            continue
        
        original_text = text_node.string
        if not original_text:
            continue
        
        new_text = original_text
        for kw in keywords:
            if kw in new_text:
                url = LINK_MAP[kw]
                # 使用正则匹配完整关键词（避免部分匹配如“植物学”）
                pattern = re.compile(r'(' + re.escape(kw) + r')')
                replacement = f'<a href="{url}">{kw}</a>'
                new_text = pattern.sub(replacement, new_text)
        
        if new_text != original_text:
            new_soup = BeautifulSoup(new_text, 'html.parser')
            text_node.replace_with(new_soup)
    
    return str(soup)

def save_article_as_html(title, content, category, summary, key_points, output_dir="articles"):
    """儲存文章為 HTML 檔案（優化版：確保標題格式、增加 meta 資訊）"""
    os.makedirs(output_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = title.replace(" ", "-").replace("/", "-").replace("?", "").replace("！", "").replace("：", "-")[:50]
    safe_title = re.sub(r'^(標題|Title)[:：]\s*', '', safe_title)
    filename = f"{date_str}-{safe_title}.html"
    filepath = os.path.join(output_dir, filename)
    category_color = CATEGORY_COLORS.get(category, "#4a7c59")
    
    content_html = add_internal_links(content)
    
    key_points_json = json.dumps(key_points, ensure_ascii=False)
    
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="description" content="{summary}">
    <meta name="article-summary" content="{summary}">
    <meta name="article-keypoints" content='{key_points_json}'>
    <meta name="article-category" content="{category}">
    <meta name="article-date" content="{date_str}">
    <meta name="author" content="蕨積 FernBrom">
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
        line-height: 1.3;
    }}
    .article-date {{
        color: var(--stone);
        margin-bottom: 2rem;
        font-size: 0.9rem;
        border-bottom: 1px solid #e0d6cc;
        padding-bottom: 1rem;
    }}
    .article-content {{
        line-height: 1.8;
        font-size: 1.05rem;
    }}
    .article-content h2 {{
        font-size: 1.5rem;
        margin: 1.5rem 0 0.8rem 0;
        color: var(--moss);
        font-family: 'Noto Serif TC', serif;
        font-weight: 600;
        border-left: 4px solid {category_color};
        padding-left: 1rem;
    }}
    .article-content h3 {{
        font-size: 1.2rem;
        margin: 1.2rem 0 0.6rem 0;
        color: var(--fern);
    }}
    .article-content p {{
        margin-bottom: 1rem;
    }}
    .article-content ul, .article-content ol {{
        margin: 1rem 0 1rem 2rem;
    }}
    .article-content li {{
        margin-bottom: 0.3rem;
    }}
    .article-content strong {{
        color: var(--moss);
        font-weight: 600;
    }}
    .article-footer {{
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid #e0d6cc;
        text-align: center;
    }}
    .back-links {{
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        flex-wrap: wrap;
        margin: 1rem 0;
    }}
    .back-links a {{
        color: var(--fern);
        text-decoration: none;
        font-size: 0.9rem;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        transition: background 0.2s;
    }}
    .back-links a:hover {{
        background: #e8e0d8;
        text-decoration: underline;
    }}
    @media (max-width: 768px) {{
        .article-title {{ font-size: 1.5rem; }}
        .article-container {{ padding: 0 1rem; }}
        .article-content h2 {{ font-size: 1.3rem; }}
        .back-links {{ gap: 0.8rem; }}
    }}
    </style>
</head>
<body>
    <div id="nav-placeholder"></div>
    <main class="content">
        <div class="article-container">
            <div class="article-category">📌 {category}</div>
            <h1 class="article-title">{title}</h1>
            <div class="article-date">📅 {date_str}</div>
            <div class="article-content">
                {content_html}
            </div>
            
            <div class="article-footer">
                <p style="color: var(--stone); font-size: 0.85rem;">🌿 每日一篇，與你一起成長</p>
                <div class="back-links">
                    <a href="index.html">🏠 返回每日文章</a>
                    <a href="{category_page}">📂 返回{category}分類</a>
                    <a href="../shop.html">🌱 植物選品</a>
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
    """產生 daily-post 目錄的索引頁面 + 分類頁面（乾淨標題列表 + 即時搜尋）"""
    
    # ========== 第一步：讀取所有文章 ==========
    articles = []
    for file in os.listdir(daily_post_dir):
        if file.endswith(".html") and file != "index.html" and len(file) >= 10 and file[4] == '-' and file[7] == '-':
            filepath = os.path.join(daily_post_dir, file)
            category = "未分類"
            title = ""
            content = ""
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
                    # 讀取文章內容（用於首頁全文顯示）
                    match_content = re.search(r'<div class="article-content">(.*?)</div>', full_content, re.DOTALL)
                    if match_content:
                        content = match_content.group(1)
            except:
                title = file.replace(".html", "").replace(date_str + "-", "").replace("-", " / ")
            articles.append({
                "filename": file,
                "date": date_str,
                "title": title,
                "category": category,
                "content": content
            })
    articles.sort(key=lambda x: x["date"], reverse=True)
    
    # ========== 第二步：處理無文章情況 ==========
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
    
    # ========== 第三步：產生主索引頁面 ==========
    latest = articles[0]
    past_articles = articles[1:]
    
    # 直接使用完整內容（保留 HTML 格式）
    full_content_html = latest.get('content', '')
    
    # 右側熱門分類與連結
    total_articles = len(articles)
    estimated_words = total_articles * 650
    
    sidebar_html = f"""
                    <div class="sidebar-col">
                        <div class="sidebar-card">
                            <h3>🌿 分類瀏覽</h3>
                            <ul class="sidebar-links">
                                <li><a href="plant.html">🌱 植物文章 <span class="count-badge">{len([a for a in articles if a['category'] == '植物'])}</span></a></li>
                                <li><a href="sustainability.html">♻️ 永續文章 <span class="count-badge">{len([a for a in articles if a['category'] == '永續'])}</span></a></li>
                                <li><a href="carbon.html">📊 碳盤查文章 <span class="count-badge">{len([a for a in articles if a['category'] == '碳盤查'])}</span></a></li>
                                <li><a href="life.html">🏡 生活文章 <span class="count-badge">{len([a for a in articles if a['category'] == '生活'])}</span></a></li>
                            </ul>
                        </div>
                        <div class="sidebar-card">
                            <h3>📊 本站統計</h3>
                            <ul class="sidebar-stats">
                                <li>📄 總文章數：<strong>{total_articles}</strong> 篇</li>
                                <li>📝 累積字數：約 <strong>{estimated_words:,}</strong> 字</li>
                                <li>📅 更新頻率：每日一篇</li>
                                <li>🌱 主題分類：4 大類</li>
                            </ul>
                        </div>
                    </div>"""
    
    past_list_html = ""
    for article in past_articles[:10]:
        past_list_html += f"""
                        <li class="past-item">
                            <a class="past-link" href="{article['filename']}">{article['title']}</a>
                            <div class="past-meta">📅 {article['date']} · {article['category']}</div>
                        </li>"""
    
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
    
    .two-columns {{ display: flex; gap: 2rem; flex-wrap: wrap; }}
    .main-col {{ flex: 3; min-width: 250px; }}
    .sidebar-col {{ flex: 1; min-width: 220px; }}
    
    .latest-article {{
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }}
    .latest-category {{
        display: inline-block;
        background: {CATEGORY_COLORS.get(latest['category'], '#4a7c59')};
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }}
    .latest-title {{ font-size: 1.8rem; color: var(--moss); margin-bottom: 0.5rem; }}
    .latest-date {{ color: var(--stone); margin-bottom: 1.5rem; font-size: 0.9rem; }}
    .latest-content {{
        line-height: 1.8;
        font-size: 1rem;
        color: #333;
    }}
    .latest-content h2 {{
        font-size: 1.4rem;
        margin: 1.2rem 0 0.8rem 0;
        color: var(--moss);
        border-left: 4px solid {CATEGORY_COLORS.get(latest['category'], '#4a7c59')};
        padding-left: 1rem;
    }}
    .latest-content h3 {{
        font-size: 1.2rem;
        margin: 1rem 0 0.5rem 0;
        color: var(--fern);
    }}
    .latest-content p {{
        margin-bottom: 0.8rem;
    }}
    .latest-content ul, .latest-content ol {{
        margin: 0.8rem 0 0.8rem 1.5rem;
    }}
    .latest-content li {{
        margin-bottom: 0.3rem;
    }}
    
    .section-title {{ font-size: 1.2rem; color: var(--moss); border-bottom: 2px solid #e0d6cc; padding-bottom: 0.5rem; margin-bottom: 1rem; }}
    .past-list {{ list-style: none; }}
    .past-item {{ margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #f0e8e0; }}
    .past-link {{ font-size: 1rem; font-weight: 500; color: var(--fern); text-decoration: none; display: block; }}
    .past-link:hover {{ text-decoration: underline; }}
    .past-meta {{ font-size: 0.75rem; color: #aaa; margin-top: 0.25rem; }}
    
    .sidebar-card {{
        background: white;
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}
    .sidebar-card h3 {{
        font-size: 1rem;
        color: var(--moss);
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0d6cc;
    }}
    .sidebar-links {{
        list-style: none;
    }}    .count-badge {{
        float: right;
        background: #e8e0d8;
        padding: 0.1rem 0.5rem;
        border-radius: 20px;
        font-size: 0.7rem;
        color: #5a7a4a;
    }}
    .sidebar-stats {{
        list-style: none;
    }}
    .sidebar-stats li {{
        margin-bottom: 0.6rem;
        font-size: 0.85rem;
        color: var(--stone);
    }}
    .sidebar-stats strong {{
        color: var(--moss);
        font-weight: 600;
    }}
    
    .sidebar-links li {{
        margin-bottom: 0.5rem;
    }}
    .sidebar-links a {{
        color: var(--stone);
        text-decoration: none;
        font-size: 0.85rem;
        transition: color 0.2s;
    }}
    .sidebar-links a:hover {{
        color: var(--fern);
        text-decoration: underline;
    }}
    
    @media (max-width: 768px) {{
        .two-columns {{ flex-direction: column; }}
        .latest-title {{ font-size: 1.4rem; }}
        .daily-container {{ padding: 0 1rem; }}
        .latest-article {{ padding: 1rem; }}
        .latest-content h2 {{ font-size: 1.2rem; }}
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
            
            <div class="two-columns">
                <div class="main-col">
                    <div class="latest-article">
                        <div class="latest-category">📌 {latest['category']}</div>
                        <h1 class="latest-title">{latest['title']}</h1>
                        <div class="latest-date">📅 {latest['date']}</div>
                        <div class="latest-content">
                            {full_content_html}
                        </div>
                    </div>
                    
                    <div class="section-title">📖 近期文章</div>
                    <ul class="past-list">
                        {past_list_html}
                    </ul>
                </div>
                
                {sidebar_html}
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
    
    # ========== 第四步：為每個分類產生獨立頁面（含搜尋功能）==========
    categories_list = ["植物", "永續", "碳盤查", "生活"]
    category_emojis = {"植物": "🌿", "永續": "♻️", "碳盤查": "📊", "生活": "🏡"}
    category_files = {"植物": "plant.html", "永續": "sustainability.html", "碳盤查": "carbon.html", "生活": "life.html"}
    
    # 準備搜尋用的 JSON 資料（所有文章）
    search_json_data = []
    for article in articles:
        search_json_data.append({
            "title": article["title"],
            "category": article["category"],
            "date": article["date"],
            "filename": article["filename"]
        })
    search_json_str = json.dumps(search_json_data, ensure_ascii=False)
    
    for current_cat in categories_list:
        cat_articles = [a for a in articles if a["category"] == current_cat]
        
        # 其他三個分類的連結
        other_cats = [c for c in categories_list if c != current_cat]
        other_links_html = ""
        for cat in other_cats:
            cat_file = category_files[cat]
            cat_emoji = category_emojis[cat]
            other_links_html += f'<a href="{cat_file}" class="category-badge">{cat_emoji} {cat}</a>'
        
        # 文章列表 HTML
        article_list_html = ""
        for article in cat_articles:
            article_list_html += f"""
                        <li class="article-list-item" data-title="{article['title']}" data-category="{article['category']}">
                            <a href="{article['filename']}" class="article-title-link">{article['title']}</a>
                            <span class="article-date">{article['date']}</span>
                        </li>"""
        
        if not article_list_html:
            article_list_html = '<li class="empty-message">📭 此分類尚無文章</li>'
        
        cat_page_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category_emojis[current_cat]} {current_cat}文章 - 蕨積每日文章</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600;900&family=Noto+Sans+TC:wght@300;400;500&family=Cormorant+Garamond:ital,wght@0,300;0,600;1,300&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>{get_template_styles()}
    .category-container {{
        max-width: 1000px;
        margin: 0 auto;
        padding: 0 2rem;
    }}
    .category-header {{
        text-align: center;
        margin-bottom: 2rem;
    }}
    .category-header h1 {{
        color: var(--moss);
        font-size: 2rem;
        font-family: 'Noto Serif TC', serif;
    }}
    .category-header p {{
        color: var(--stone);
        margin-top: 0.5rem;
    }}
    
    .search-box {{
        max-width: 320px;
        margin: 0 auto 2rem auto;
    }}
    .search-input {{
        width: 100%;
        padding: 0.6rem 1rem;
        font-size: 0.9rem;
        border: 1px solid #e0d6cc;
        border-radius: 40px;
        background: white;
        font-family: 'Noto Sans TC', sans-serif;
        transition: all 0.2s;
        text-align: center;
    }}
    .search-input:focus {{
        outline: none;
        border-color: var(--fern);
        box-shadow: 0 0 0 3px rgba(90,122,74,0.1);
    }}
    .search-input::placeholder {{
        text-align: center;
        font-size: 0.85rem;
    }}
    
    .other-categories {{
        display: flex;
        justify-content: center;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid #f0e8e0;
    }}
    .category-badge {{
        display: inline-block;
        padding: 0.4rem 1.2rem;
        background: #e8e0d8;
        color: #4a5b4e;
        border-radius: 30px;
        text-decoration: none;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.2s;
    }}
    .category-badge:hover {{
        background: var(--fern);
        color: white;
        transform: translateY(-2px);
    }}
    
    .section-title {{
        font-size: 1.2rem;
        color: var(--moss);
        border-bottom: 2px solid #e0d6cc;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }}
    .result-count {{
        font-size: 0.8rem;
        color: var(--stone);
        font-weight: normal;
    }}
    .article-list {{
        list-style: none;
    }}
    .article-list-item {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.8rem 0;
        border-bottom: 1px solid #f0e8e0;
        transition: background 0.2s;
    }}
    .article-list-item:hover {{
        background: #faf7f2;
        padding-left: 0.5rem;
    }}
    .article-title-link {{
        font-size: 1rem;
        font-weight: 500;
        color: var(--fern);
        text-decoration: none;
        flex: 1;
    }}
    .article-title-link:hover {{
        text-decoration: underline;
    }}
    .article-date {{
        font-size: 0.75rem;
        color: #aaa;
        font-family: monospace;
        margin-left: 1rem;
        white-space: nowrap;
    }}
    .empty-message {{
        text-align: center;
        color: var(--stone);
        padding: 2rem;
    }}
    .no-results {{
        text-align: center;
        color: var(--stone);
        padding: 2rem;
        font-style: italic;
    }}
    
    @media (max-width: 768px) {{
        .category-container {{ padding: 0 1rem; }}
        .article-list-item {{
            flex-direction: column;
            align-items: flex-start;
            gap: 0.3rem;
        }}
        .article-date {{
            margin-left: 0;
            font-size: 0.7rem;
        }}
    }}
    </style>
</head>
<body>
    <div id="nav-placeholder"></div>
    
    <main class="content">
        <div class="category-container">
            <div class="category-header">
                <h1>{category_emojis[current_cat]} {current_cat}文章</h1>
                <p>蕨積每日文章 - {current_cat}分類精選</p>
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" class="search-input" placeholder="🔍 搜尋標題或分類... (即時篩選)" autocomplete="off">
            </div>
            
            <div class="other-categories">
                {other_links_html}
            </div>
            
            <div class="section-title">
                <span>📖 文章列表</span>
                <span class="result-count" id="resultCount">共 {len(cat_articles)} 篇</span>
            </div>
            
            <ul class="article-list" id="articleList">
                {article_list_html}
            </ul>
        </div>
    </main>
    
    {get_footer_html()}
    
    <script>
        {get_nav_script()}
        
        const searchInput = document.getElementById('searchInput');
        const articleList = document.getElementById('articleList');
        const resultCount = document.getElementById('resultCount');
        
        const allArticles = {search_json_str};
        const currentCategory = '{current_cat}';
        
        function renderFilteredArticles(keyword) {{
            let filtered = allArticles.filter(article => article.category === currentCategory);
            
            if (keyword.trim() !== '') {{
                const lowerKeyword = keyword.toLowerCase();
                filtered = allArticles.filter(article => 
                    article.title.toLowerCase().includes(lowerKeyword) || 
                    article.category.toLowerCase().includes(lowerKeyword)
                );
            }}
            
            resultCount.textContent = `共 ${{filtered.length}} 篇`;
            
            if (filtered.length === 0) {{
                articleList.innerHTML = '<li class="no-results">🔍 沒有找到相關文章，試試其他關鍵字～</li>';
                return;
            }}
            
            let html = '';
            filtered.forEach(article => {{
                html += `
                    <li class="article-list-item">
                        <a href="${{article.filename}}" class="article-title-link">${{article.title}}</a>
                        <span class="article-date">${{article.date}}</span>
                    </li>
                `;
            }});
            articleList.innerHTML = html;
        }}
        
        searchInput.addEventListener('input', (e) => {{
            renderFilteredArticles(e.target.value);
        }});
    </script>
</body>
</html>"""
        
        cat_filepath = os.path.join(daily_post_dir, category_files[current_cat])
        with open(cat_filepath, "w", encoding="utf-8") as f:
            f.write(cat_page_html)
        print(f"📁 已產生分類頁面：{category_files[current_cat]} (含搜尋功能)")

# ==================== 推送 ====================
def commit_and_push_to_website():
    """推送到網站倉庫"""
    print("=" * 50)
    print("開始推送到網站倉庫...")
    username = os.getenv("GITHUB_USERNAME", "fangyung0323")
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
        
        # 複製文章
        copied_count = 0
        if os.path.exists("articles"):
            for f in os.listdir("articles"):
                if f.endswith(".html"):
                    src = os.path.join("articles", f)
                    dst = os.path.join(daily_dir, f)
                    shutil.copy2(src, dst)
                    copied_count += 1
                    print(f"📄 複製: {f}")
        
        print(f"✅ 已複製 {copied_count} 篇文章到 daily-post")
        
        # 產生 index 和分類頁面
        generate_daily_post_index(daily_dir)
        
        # Git 設定
        subprocess.run(["git", "config", "user.name", "jueji-bot"], cwd=website_dir, check=False)
        subprocess.run(["git", "config", "user.email", "bot@jueji.com"], cwd=website_dir, check=False)
        subprocess.run(["git", "add", "daily-post/"], cwd=website_dir, check=True)
        
        # 檢查狀態
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
    print("🌿 蕨積每日發文機器人啟動 (70%原創觀點版)")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ========== 防重複檢查 ==========
    if check_today_article_exists():
        print("❌ 今天已經有文章了，跳過本次發文（避免重複）")
        print("💡 如需強制發文，請手動刪除今天的文章後再執行")
        return    # ================================
    
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
