#!/usr/bin/env python3
"""
台灣 ESG / 植生牆 / 碳盤查 / 生活 新聞爬蟲
產生 JSON 資料和靜態 HTML 網頁
"""

import os
import json
import re
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

# ==================== 設定 ====================
# 專案根目錄（假設 scripts 在 fbnote 倉庫根目錄下）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_DATA_DIR = os.path.join(BASE_DIR, "news-data")
NEWS_PAGES_DIR = os.path.join(BASE_DIR, "news-pages")

# 確保目錄存在
os.makedirs(NEWS_DATA_DIR, exist_ok=True)
os.makedirs(NEWS_PAGES_DIR, exist_ok=True)

# 新聞來源設定
NEWS_SOURCES = {
    "環境資訊中心": {
        "url": "https://e-info.org.tw/",
        "search_url": "https://e-info.org.tw/search?q={keyword}",
        "category_keywords": {
            "植生牆": ["植生牆", "垂直綠化", "綠牆", "立面綠化"],
            "ESG": ["ESG", "永續發展", "企業社會責任", "永續報告"],
            "碳盤查": ["碳盤查", "碳足跡", "碳中和", "淨零排放", "溫室氣體"],
            "生活": ["綠色生活", "環保生活", "永續生活", "零廢棄"]
        }
    },
    "CSR天下": {
        "url": "https://csr.cw.com.tw/",
        "search_url": "https://csr.cw.com.tw/search?q={keyword}",
        "category_keywords": {}  # 繼承上面的關鍵字
    },
    "倡議家": {
        "url": "https://ubrand.udn.com/",
        "search_url": "https://ubrand.udn.com/search?q={keyword}",
        "category_keywords": {}
    }
}

# ==================== 新聞資料結構 ====================
class NewsItem:
    def __init__(self, title: str, source: str, url: str, date: str, 
                 summary: str, content: str = "", category: str = ""):
        self.title = title
        self.source = source
        self.url = url
        self.date = date
        self.summary = summary
        self.content = content
        self.category = category
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "date": self.date,
            "summary": self.summary,
            "content": self.content[:500] if self.content else "",  # 只保留前500字
            "category": self.category
        }

# ==================== 模擬爬蟲（因為實際網站可能有反爬機制）====================
# 注意：這是一個示範用的模擬資料
# 實際使用時需要根據目標網站的結構編寫真實的爬蟲邏輯

def fetch_mock_news() -> Dict[str, List[NewsItem]]:
    """
    產生模擬新聞資料（示範用）
    實際使用時請替換成真實的爬蟲邏輯
    """
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    
    mock_news = {
        "植生牆": [
            NewsItem(
                title="北市推建築物植生牆補助 每坪最高3000元",
                source="自由時報",
                url="https://example.com/news/1",
                date=today,
                summary="台北市都發局宣布，為推動城市綠化，將補助既有建築物設置植生牆，每坪最高補助3000元，申請期限至6月底。",
                content="台北市都發局今日召開記者會，宣布推出「建築物植生牆設置補助計畫」。局長表示，這是為了因應氣候變遷，提高城市綠覆率。補助對象為台北市既有建築物，包含住宅、辦公大樓、學校等。每案最高補助新台幣30萬元，申請期限至今年6月30日止。",
                category="植生牆"
            ),
            NewsItem(
                title="研究：辦公室的植生牆可提升15%工作效率",
                source="環境資訊中心",
                url="https://example.com/news/2",
                date=yesterday,
                summary="最新研究顯示，辦公室設置植生牆不僅能淨化空氣，還能提升員工15%的工作效率，降低22%的壓力指數。",
                content="荷蘭烏特勒支大學最新研究發現，在辦公室設置植生牆後，員工的工作效率平均提升15%，壓力指數降低22%，缺勤率也下降了18%。研究團隊追蹤了12家企業，為期6個月。",
                category="植生牆"
            )
        ],
        "ESG": [
            NewsItem(
                title="台灣企業ESG評比出爐 台積電蟬聯榜首",
                source="CSR天下",
                url="https://example.com/news/3",
                date=today,
                summary="2026年台灣企業ESG評比結果公布，台積電在環境、社會、治理三面向均獲高分，連續三年排名第一。",
                content="天下雜誌今日公布2026年台灣企業ESG評比結果，共評比500家上市櫃公司。台積電在碳排放減量、員工福利、公司治理等項目均獲滿分。",
                category="ESG"
            )
        ],
        "碳盤查": [
            NewsItem(
                title="中小企業碳盤查補助方案 最高可申請20萬",
                source="經濟日報",
                url="https://example.com/news/4",
                date=yesterday,
                summary="經濟部推出中小企業碳盤查補助方案，每家企業最高可申請20萬元，協助企業導入碳管理系統。",
                content="經濟部中小企業處今日宣布，為協助中小企業因應淨零排放趨勢，將補助企業進行碳盤查及導入碳管理系統。",
                category="碳盤查"
            )
        ],
        "生活": [
            NewsItem(
                title="零廢棄生活正夯 環保容器租借服務進駐台北",
                source="倡議家",
                url="https://example.com/news/5",
                date=two_days_ago,
                summary="主打循環經濟的環保容器租借服務「好盒器」進駐台北，民眾購買外帶餐飲時可租借可重複使用的容器。",
                content="新創團隊「好盒器」今日宣布，已在台北設立10個環保容器租借站點。民眾購買外帶餐飲時，可掃描QR Code租借容器，用完後歸還即可。",
                category="生活"
            )
        ]
    }
    return mock_news

# ==================== 真實爬蟲範例（需根據目標網站調整）====================
def fetch_rss_news(rss_url: str, source_name: str) -> List[NewsItem]:
    """
    從 RSS 訂閱抓取新聞（較容易實作）
    """
    news_items = []
    try:
        response = requests.get(rss_url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        # 這裡需要解析 RSS XML
        # 因為不同網站的 RSS 格式不同，需要根據實際情況編寫
        pass
    except Exception as e:
        print(f"RSS 抓取失敗 {source_name}: {e}")
    return news_items

# ==================== 儲存 JSON ====================
def save_to_json(all_news: Dict[str, List[NewsItem]]):
    """將新聞儲存為 JSON 檔案"""
    for category, news_list in all_news.items():
        if not news_list:
            continue
        
        # 對應的檔案名稱
        file_map = {
            "植生牆": "green_wall.json",
            "ESG": "esg.json",
            "碳盤查": "carbon.json",
            "生活": "life.json"
        }
        
        filename = file_map.get(category)
        if not filename:
            continue
        
        filepath = os.path.join(NEWS_DATA_DIR, filename)
        
        # 讀取現有資料（如果有的話）
        existing_news = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_news = json.load(f)
            except:
                existing_news = []
        
        # 合併新資料（避免重複，根據 URL 判斷）
        existing_urls = {item.get("url") for item in existing_news}
        new_items = [item.to_dict() for item in news_list if item.url not in existing_urls]
        
        if new_items:
            all_items = new_items + existing_news
            # 按日期排序（最新的在前）
            all_items.sort(key=lambda x: x.get("date", ""), reverse=True)
            # 只保留最近 30 筆
            all_items = all_items[:30]
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(all_items, f, ensure_ascii=False, indent=2)
            print(f"✅ 儲存 {category} 新聞：新增 {len(new_items)} 筆")
        else:
            print(f"📭 {category} 無新增新聞")

# ==================== 生成靜態 HTML 網頁 ====================
def generate_html_pages(all_news: Dict[str, List[NewsItem]]):
    """生成給 AI 讀取的靜態 HTML 網頁"""
    
    category_names = ["植生牆", "ESG", "碳盤查", "生活"]
    category_files = {
        "植生牆": "plant-news.html",
        "ESG": "esg-news.html",
        "碳盤查": "carbon-news.html",
        "生活": "life-news.html"
    }
    category_colors = {
        "植生牆": "#4a7c59",
        "ESG": "#2c7a4d",
        "碳盤查": "#1e6f5c",
        "生活": "#b88b4a"
    }
    
    # 產生總覽首頁
    homepage_html = generate_homepage(all_news, category_names, category_files)
    with open(os.path.join(NEWS_PAGES_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(homepage_html)
    print("✅ 產生總覽首頁: news-pages/index.html")
    
    # 為每個分類產生獨立頁面
    for category in category_names:
        news_list = all_news.get(category, [])
        page_html = generate_category_page(category, news_list, category_colors.get(category, "#4a7c59"))
        
        filename = category_files[category]
        with open(os.path.join(NEWS_PAGES_DIR, filename), "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"✅ 產生分類頁面: news-pages/{filename}")


def generate_homepage(all_news: Dict, category_names: List[str], category_files: Dict) -> str:
    """產生新聞總覽首頁（簡潔版，適合快速瀏覽）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 統計各分類數量
    category_counts = {cat: len(all_news.get(cat, [])) for cat in category_names}
    
    # 各分類的最新 3 則新聞
    preview_html = ""
    for cat in category_names:
        news_list = all_news.get(cat, [])[:3]
        if news_list:
            items_html = ""
            for news in news_list:
                items_html += f"""
                <li><a href="{news.url}" target="_blank">{news.title}</a>
                <span class="date">{news.date}</span></li>"""
            
            preview_html += f"""
            <div class="category-preview">
                <h2><a href="{category_files[cat]}">{cat}</a> 
                <span class="count">({category_counts[cat]} 則)</span></h2>
                <ul>{items_html}</ul>
            </div>"""
    
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESG／植生牆／碳盤查 台灣新聞摘要</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Noto Sans TC', -apple-system, sans-serif;
            background: #f5f0e8;
            color: #1a1a14;
            line-height: 1.6;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        h1 {{
            color: #3d5a38;
            border-bottom: 3px solid #8aab7a;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}
        .update-info {{
            color: #9a9080;
            font-size: 0.85rem;
            margin-bottom: 2rem;
            text-align: right;
        }}
        .category-preview {{
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e0d6cc;
        }}
        .category-preview h2 {{
            font-size: 1.3rem;
            margin-bottom: 0.8rem;
        }}
        .category-preview h2 a {{
            color: #3d5a38;
            text-decoration: none;
        }}
        .category-preview h2 a:hover {{
            text-decoration: underline;
        }}
        .count {{
            font-size: 0.85rem;
            color: #9a9080;
            font-weight: normal;
        }}
        .category-preview ul {{
            list-style: none;
        }}
        .category-preview li {{
            padding: 0.5rem 0;
            border-bottom: 1px dashed #e0d6cc;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }}
        .category-preview li a {{
            color: #5a7a4a;
            text-decoration: none;
            flex: 1;
        }}
        .category-preview li a:hover {{
            text-decoration: underline;
        }}
        .date {{
            color: #9a9080;
            font-size: 0.8rem;
            margin-left: 1rem;
        }}
        .footer {{
            margin-top: 2rem;
            padding-top: 1rem;
            text-align: center;
            font-size: 0.8rem;
            color: #9a9080;
            border-top: 1px solid #e0d6cc;
        }}
        @media (max-width: 600px) {{
            .container {{ padding: 1rem; }}
            .category-preview li {{
                flex-direction: column;
            }}
            .date {{ margin-left: 0; margin-top: 0.2rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 ESG · 植生牆 · 碳盤查 · 永續生活</h1>
        <div class="update-info">📅 更新時間：{now}</div>
        
        {preview_html}
        
        <div class="footer">
            <p>🤖 本頁由自動爬蟲產生，資料僅供 AI 文章生成參考</p>
            <p>資料來源：環境資訊中心、CSR天下、倡議家、自由時報、經濟日報等</p>
        </div>
    </div>
</body>
</html>"""


def generate_category_page(category: str, news_list: List[NewsItem], color: str) -> str:
    """產生單一分類的新聞頁面（乾淨結構，適合 AI 閱讀）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not news_list:
        return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head><meta charset="UTF-8"><title>{category} 新聞摘要</title></head>
<body>
<h1>{category} 新聞摘要</h1>
<p>📭 目前尚無相關新聞資料</p>
<p>更新時間：{now}</p>
</body>
</html>"""
    
    news_items_html = ""
    for news in news_list:
        key_points_html = ""
        # 如果有重點摘要的欄位，可以特別標記
        if hasattr(news, 'key_points') and news.key_points:
            key_points_html = "<div class='key-points'><strong>重點：</strong><ul>" + \
                              "".join(f"<li>{kp}</li>" for kp in news.key_points) + "</ul></div>"
        
        news_items_html += f"""
        <div class="news-item">
            <h2>{news.title}</h2>
            <div class="meta">
                📰 來源：{news.source} | 📅 日期：{news.date}
            </div>
            <div class="summary">
                <strong>摘要：</strong>{news.summary}
            </div>
            {key_points_html}
            <div class="full-text" style="display:none;">
                {news.content}
            </div>
            <div class="source-link">
                🔗 原文：<a href="{news.url}" target="_blank">{news.url}</a>
            </div>
        </div>"""
    
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} 新聞摘要 - 提供 AI 參考</title>
    <meta name="description" content="爬蟲收集的{category}相關新聞，供AI文章生成參考">
    <meta name="robots" content="noindex, nofollow">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Noto Sans TC', -apple-system, sans-serif;
            background: #faf7f2;
            color: #1a1a14;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        h1 {{
            color: {color};
            border-bottom: 2px solid {color};
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}
        .update-info {{
            color: #9a9080;
            font-size: 0.8rem;
            margin-bottom: 1.5rem;
        }}
        .news-item {{
            background: white;
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            border-left: 4px solid {color};
        }}
        .news-item h2 {{
            font-size: 1.2rem;
            color: {color};
            margin-bottom: 0.4rem;
        }}
        .meta {{
            font-size: 0.75rem;
            color: #9a9080;
            margin-bottom: 0.8rem;
        }}
        .summary {{
            margin-bottom: 0.6rem;
            line-height: 1.5;
        }}
        .key-points {{
            background: #f0f0e8;
            padding: 0.6rem;
            border-radius: 8px;
            margin: 0.6rem 0;
            font-size: 0.9rem;
        }}
        .key-points ul {{
            margin-left: 1.2rem;
        }}
        .source-link {{
            font-size: 0.75rem;
            margin-top: 0.6rem;
        }}
        .source-link a {{
            color: {color};
            text-decoration: none;
            word-break: break-all;
        }}
        hr {{
            margin: 1rem 0;
            border: none;
            border-top: 1px solid #e0d6cc;
        }}
        .footer {{
            text-align: center;
            font-size: 0.75rem;
            color: #9a9080;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #e0d6cc;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 {category} 相關新聞摘要</h1>
        <div class="update-info">📅 更新時間：{now} | 共 {len(news_list)} 則新聞</div>
        
        {news_items_html}
        
        <div class="footer">
            <p>🤖 本頁資料由自動爬蟲產生，提供 AI 文章生成參考使用</p>
            <p>⚠️ 資料僅供參考，請自行確認原始來源</p>
        </div>
    </div>
</body>
</html>"""


# ==================== 主程式 ====================
def main():
    print("=" * 50)
    print("🌿 台灣 ESG / 植生牆 / 碳盤查 新聞爬蟲")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 目前使用模擬資料（示範用）
    # TODO: 替換成真實的爬蟲邏輯
    print("📡 開始爬取新聞...")
    all_news = fetch_mock_news()
    
    # 顯示統計
    for category, news_list in all_news.items():
        print(f"  {category}: {len(news_list)} 則")
    
    # 儲存 JSON
    print("\n💾 儲存 JSON 資料...")
    save_to_json(all_news)
    
    # 產生靜態 HTML 網頁
    print("\n📄 產生靜態 HTML 網頁...")
    generate_html_pages(all_news)
    
    print("\n✅ 爬蟲執行完畢！")
    print(f"📁 JSON 資料位置: {NEWS_DATA_DIR}")
    print(f"📁 HTML 頁面位置: {NEWS_PAGES_DIR}")


if __name__ == "__main__":
    main()
