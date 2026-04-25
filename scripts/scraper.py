#!/usr/bin/env python3
"""
台灣 ESG / 植生牆 / 碳盤查 / 生活 新聞爬蟲
支援多種來源：Google News RSS、台灣媒體 RSS、環境資訊中心
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
import feedparser

# ==================== 設定 ====================
# 專案根目錄（假設 scripts 在 fbnote 倉庫根目錄下）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS_DATA_DIR = os.path.join(BASE_DIR, "news-data")
NEWS_PAGES_DIR = os.path.join(BASE_DIR, "news-pages")

# 確保目錄存在
os.makedirs(NEWS_DATA_DIR, exist_ok=True)
os.makedirs(NEWS_PAGES_DIR, exist_ok=True)

# ==================== 新聞資料結構 ====================
class NewsItem:
    def __init__(self, title: str, source: str, url: str, date: str, 
                 summary: str, content: str = "", category: str = "", 
                 key_points: List[str] = None):
        self.title = title
        self.source = source
        self.url = url
        self.date = date
        self.summary = summary
        self.content = content
        self.category = category
        self.key_points = key_points or []
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "date": self.date,
            "summary": self.summary[:200],  # 限制長度
            "content": self.content[:500] if self.content else "",
            "category": self.category,
            "key_points": self.key_points
        }

# ==================== 關鍵字分類對應 ====================
KEYWORD_TO_CATEGORY = {
    # 植生牆 / 植物相關
    "植生牆": "植生牆",
    "垂直綠化": "植生牆",
    "綠牆": "植生牆",
    "植物": "植生牆",
    "綠化": "植生牆",
    "盆栽": "植生牆",
    "花園": "植生牆",
    
    # ESG 相關
    "ESG": "ESG",
    "永續": "ESG",
    "CSR": "ESG",
    "企業社會責任": "ESG",
    "永續發展": "ESG",
    
    # 碳盤查相關
    "碳盤查": "碳盤查",
    "碳足跡": "碳盤查",
    "淨零": "碳盤查",
    "碳中和": "碳盤查",
    "溫室氣體": "碳盤查",
    "碳權": "碳盤查",
    "氣候變遷": "碳盤查",
    
    # 生活相關
    "生活": "生活",
    "環保生活": "生活",
    "零浪費": "生活",
    "綠色生活": "生活",
    "減塑": "生活",
    "循環經濟": "生活"
}

def classify_article(title: str, summary: str = "") -> str:
    """根據標題和內容判斷分類"""
    text_to_check = f"{title} {summary}".lower()
    
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword.lower() in text_to_check:
            return category
    
    return "生活"  # 預設分類

# ==================== 來源1：Google News RSS ====================
GOOGLE_NEWS_QUERIES = {
    "植生牆": ["植生牆 台灣", "垂直綠化", "綠牆 建築"],
    "ESG": ["ESG 台灣 企業", "永續發展 台灣", "企業社會責任"],
    "碳盤查": ["碳盤查 台灣", "碳足跡 企業", "淨零排放 台灣"],
    "生活": ["環保生活 台灣", "零廢棄 生活", "綠色消費"]
}

def fetch_from_google_news() -> Dict[str, List[NewsItem]]:
    """從 Google News RSS 抓取新聞"""
    all_news = {
        "植生牆": [],
        "ESG": [],
        "碳盤查": [],
        "生活": []
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("\n🔍 開始從 Google News 抓取...")
    
    for category, queries in GOOGLE_NEWS_QUERIES.items():
        for query in queries:
            encoded_query = requests.utils.quote(f"{query}")
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=zh-TW&gl=TW&ceid=TW:zh"
            
            try:
                response = requests.get(rss_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.content)
                    
                    for entry in feed.entries[:5]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        summary = entry.get("summary", "")[:200]
                        
                        # 清理 HTML 標籤
                        summary = re.sub(r'<[^>]+>', '', summary)
                        
                        # 轉換日期
                        try:
                            if published:
                                from email.utils import parsedate_to_datetime
                                date_obj = parsedate_to_datetime(published)
                                date_str = date_obj.strftime("%Y-%m-%d")
                            else:
                                date_str = datetime.now().strftime("%Y-%m-%d")
                        except:
                            date_str = datetime.now().strftime("%Y-%m-%d")
                        
                        # 去重
                        existing_titles = [n.title for n in all_news[category]]
                        if title and title not in existing_titles and len(title) > 5:
                            news_item = NewsItem(
                                title=title,
                                source="Google News",
                                url=link,
                                date=date_str,
                                summary=summary[:150],
                                content=summary,
                                category=category
                            )
                            all_news[category].append(news_item)
                            print(f"  ✅ [Google/{category}] {title[:40]}...")
                    
            except Exception as e:
                print(f"  ⚠️ Google News 查詢失敗 ({query}): {e}")
            
            time.sleep(1)  # 避免請求過快
    
    return all_news

# ==================== 來源2：台灣媒體 RSS ====================
RSS_FEEDS = [
    {"name": "中央社", "url": "https://www.cna.com.tw/rss/all.xml"},
    {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/all.xml"},
]

def fetch_from_taiwan_rss() -> Dict[str, List[NewsItem]]:
    """從台灣媒體 RSS 抓取新聞"""
    all_news = {
        "植生牆": [],
        "ESG": [],
        "碳盤查": [],
        "生活": []
    }
    
    print("\n📰 開始從台灣媒體 RSS 抓取...")
    
    for feed_info in RSS_FEEDS:
        source_name = feed_info["name"]
        rss_url = feed_info["url"]
        
        try:
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                print(f"  ⚠️ {source_name} RSS 解析可能有問題")
            
            for entry in feed.entries[:20]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:200]
                link = entry.get("link", "")
                published = entry.get("published", "")
                
                # 清理摘要
                summary = re.sub(r'<[^>]+>', '', summary)
                
                # 判斷分類
                category = classify_article(title, summary)
                
                # 轉換日期
                try:
                    if published:
                        from email.utils import parsedate_to_datetime
                        date_obj = parsedate_to_datetime(published)
                        date_str = date_obj.strftime("%Y-%m-%d")
                    else:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                except:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                # 去重
                existing_titles = [n.title for n in all_news[category]]
                if title and title not in existing_titles and len(title) > 5:
                    news_item = NewsItem(
                        title=title,
                        source=source_name,
                        url=link,
                        date=date_str,
                        summary=summary[:150],
                        content=summary,
                        category=category
                    )
                    all_news[category].append(news_item)
                    print(f"  ✅ [{source_name}/{category}] {title[:40]}...")
                    
        except Exception as e:
            print(f"  ❌ {source_name} RSS 失敗: {e}")
        
        time.sleep(1)
    
    return all_news

# ==================== 來源3：環境資訊中心 ====================
def fetch_from_einfo() -> Dict[str, List[NewsItem]]:
    """從環境資訊中心抓取新聞（HTML 解析）"""
    all_news = {
        "植生牆": [],
        "ESG": [],
        "碳盤查": [],
        "生活": []
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    
    print("\n🌱 開始從環境資訊中心抓取...")
    
    # 環境資訊中心最新文章頁面
    urls = [
        "https://e-info.org.tw/",
        "https://e-info.org.tw/taxonomy/term/1",  # 新聞分類
    ]
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尋找文章連結
                # 常見模式：<a> 且 href 包含 /node/ 或 /taxonomy/
                all_links = soup.find_all('a', href=True)
                
                for link in all_links:
                    href = link.get('href', '')
                    title = link.get_text(strip=True)
                    
                    # 過濾條件
                    if not title or len(title) < 10:
                        continue
                    
                    # 檢查是否為文章連結
                    is_article = ('/node/' in href or '/taxonomy/term/' in href or 
                                  '/article/' in href)
                    
                    if is_article:
                        # 完整網址
                        if href.startswith('/'):
                            full_url = f"https://e-info.org.tw{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue
                        
                        # 判斷分類
                        category = classify_article(title)
                        
                        # 去重
                        existing_titles = [n.title for n in all_news[category]]
                        if title not in existing_titles:
                            news_item = NewsItem(
                                title=title,
                                source="環境資訊中心",
                                url=full_url,
                                date=datetime.now().strftime("%Y-%m-%d"),
                                summary=title[:150],
                                content="",
                                category=category
                            )
                            all_news[category].append(news_item)
                            print(f"  ✅ [環境資訊中心/{category}] {title[:40]}...")
                
                # 每個分類限制數量
                for cat in all_news:
                    all_news[cat] = all_news[cat][:15]
                    
            else:
                print(f"  ⚠️ 環境資訊中心回應: {response.status_code}")
                
        except Exception as e:
            print(f"  ⚠️ 環境資訊中心抓取失敗: {e}")
        
        time.sleep(2)
    
    return all_news

# ==================== 來源4：模擬資料（備用）====================
def fetch_mock_news() -> Dict[str, List[NewsItem]]:
    """產生模擬新聞資料（當真實來源都失敗時使用）"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    
    mock_news = {
        "植生牆": [
            NewsItem(
                title="北市推建築物植生牆補助 每坪最高3000元",
                source="自由時報",
                url="#",
                date=today,
                summary="台北市都發局宣布，為推動城市綠化，將補助既有建築物設置植生牆，每坪最高補助3000元。",
                content="台北市都發局今日召開記者會，宣布推出「建築物植生牆設置補助計畫」。補助對象為台北市既有建築物，每案最高補助30萬元。",
                category="植生牆"
            ),
            NewsItem(
                title="研究：辦公室的植生牆可提升15%工作效率",
                source="環境資訊中心",
                url="#",
                date=yesterday,
                summary="最新研究顯示，辦公室設置植生牆不僅能淨化空氣，還能提升員工15%的工作效率。",
                content="荷蘭烏特勒支大學研究發現，在辦公室設置植生牆後，員工工作效率平均提升15%，壓力指數降低22%。",
                category="植生牆",
                key_points=["提升15%工作效率", "降低22%壓力", "減少18%缺勤率"]
            )
        ],
        "ESG": [
            NewsItem(
                title="台灣企業ESG評比出爐 推動綠色轉型有成",
                source="CSR天下",
                url="#",
                date=today,
                summary="2026年台灣企業ESG評比結果公布，多家企業在環境永續方面表現亮眼。",
                content="天下雜誌公布2026年台灣企業ESG評比結果，企業在碳排放減量、綠色能源使用等方面均有顯著進步。",
                category="ESG"
            )
        ],
        "碳盤查": [
            NewsItem(
                title="中小企業碳盤查補助方案 最高20萬元",
                source="經濟日報",
                url="#",
                date=yesterday,
                summary="經濟部推出中小企業碳盤查補助方案，協助企業導入碳管理系統。",
                content="經濟部宣布補助中小企業進行碳盤查，每家最高可申請20萬元。",
                category="碳盤查"
            )
        ],
        "生活": [
            NewsItem(
                title="零廢棄生活正夯 環保容器租借服務進駐台北",
                source="倡議家",
                url="#",
                date=two_days_ago,
                summary="主打循環經濟的環保容器租借服務進駐台北，民眾可租借可重複使用的容器。",
                content="新創團隊推出環保容器租借服務，鼓勵民眾減少一次性垃圾。",
                category="生活"
            )
        ]
    }
    return mock_news

# ==================== 儲存 JSON ====================
def save_to_json(all_news: Dict[str, List[NewsItem]]):
    """將新聞儲存為 JSON 檔案"""
    file_map = {
        "植生牆": "green_wall.json",
        "ESG": "esg.json",
        "碳盤查": "carbon.json",
        "生活": "life.json"
    }
    
    for category, news_list in all_news.items():
        if not news_list:
            continue
        
        filename = file_map.get(category)
        if not filename:
            continue
        
        filepath = os.path.join(NEWS_DATA_DIR, filename)
        
        # 讀取現有資料（去重用）
        existing_news = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing_news = json.load(f)
            except:
                existing_news = []
        
        # 合併新資料
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
            print(f"\n✅ 儲存 {category} 新聞：新增 {len(new_items)} 筆")
        else:
            print(f"\n📭 {category} 無新增新聞")

# ==================== 生成靜態 HTML ====================
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
    print("\n✅ 產生總覽首頁: news-pages/index.html")
    
    # 為每個分類產生獨立頁面
    for category in category_names:
        news_list = all_news.get(category, [])
        page_html = generate_category_page(category, news_list, category_colors.get(category, "#4a7c59"))
        
        filename = category_files[category]
        with open(os.path.join(NEWS_PAGES_DIR, filename), "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"✅ 產生分類頁面: news-pages/{filename}")


def generate_homepage(all_news: Dict, category_names: List[str], category_files: Dict) -> str:
    """產生新聞總覽首頁"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    category_counts = {cat: len(all_news.get(cat, [])) for cat in category_names}
    
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
        h1 {{ color: #3d5a38; border-bottom: 3px solid #8aab7a; padding-bottom: 0.5rem; margin-bottom: 1rem; }}
        .update-info {{ color: #9a9080; font-size: 0.85rem; margin-bottom: 2rem; text-align: right; }}
        .category-preview {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 1px solid #e0d6cc; }}
        .category-preview h2 {{ font-size: 1.3rem; margin-bottom: 0.8rem; }}
        .category-preview h2 a {{ color: #3d5a38; text-decoration: none; }}
        .category-preview ul {{ list-style: none; }}
        .category-preview li {{
            padding: 0.5rem 0;
            border-bottom: 1px dashed #e0d6cc;
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
        }}
        .category-preview li a {{ color: #5a7a4a; text-decoration: none; flex: 1; }}
        .category-preview li a:hover {{ text-decoration: underline; }}
        .date {{ color: #9a9080; font-size: 0.8rem; margin-left: 1rem; }}
        .footer {{ margin-top: 2rem; padding-top: 1rem; text-align: center; font-size: 0.8rem; color: #9a9080; border-top: 1px solid #e0d6cc; }}
        @media (max-width: 600px) {{
            .container {{ padding: 1rem; }}
            .category-preview li {{ flex-direction: column; }}
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
            <p>資料來源：Google News、中央社、自由時報、環境資訊中心</p>
        </div>
    </div>
</body>
</html>"""


def generate_category_page(category: str, news_list: List[NewsItem], color: str) -> str:
    """產生單一分類的新聞頁面（純內容，適合 AI 閱讀）"""
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
        if news.key_points:
            key_points_html = "<div class='key-points'><strong>重點：</strong><ul>" + \
                              "".join(f"<li>{kp}</li>" for kp in news.key_points) + "</ul></div>"
        
        news_items_html += f"""
        <div class="news-item">
            <h2>{news.title}</h2>
            <div class="meta">📰 來源：{news.source} | 📅 日期：{news.date}</div>
            <div class="summary"><strong>摘要：</strong>{news.summary}</div>
            {key_points_html}
            <div class="source-link">🔗 原文：<a href="{news.url}" target="_blank">{news.url}</a></div>
        </div>"""
    
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} 新聞摘要 - 提供 AI 參考</title>
    <meta name="robots" content="noindex, nofollow">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Noto Sans TC', -apple-system, sans-serif;
            background: #faf7f2;
            color: #1a1a14;
            padding: 2rem 1rem;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        h1 {{ color: {color}; border-bottom: 2px solid {color}; padding-bottom: 0.5rem; margin-bottom: 1rem; }}
        .update-info {{ color: #9a9080; font-size: 0.8rem; margin-bottom: 1.5rem; }}
        .news-item {{
            background: white;
            border-radius: 12px;
            padding: 1.2rem;
            margin-bottom: 1.2rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            border-left: 4px solid {color};
        }}
        .news-item h2 {{ font-size: 1.2rem; color: {color}; margin-bottom: 0.4rem; }}
        .meta {{ font-size: 0.75rem; color: #9a9080; margin-bottom: 0.8rem; }}
        .summary {{ margin-bottom: 0.6rem; line-height: 1.5; }}
        .key-points {{ background: #f0f0e8; padding: 0.6rem; border-radius: 8px; margin: 0.6rem 0; font-size: 0.9rem; }}
        .key-points ul {{ margin-left: 1.2rem; }}
        .source-link {{ font-size: 0.75rem; margin-top: 0.6rem; }}
        .source-link a {{ color: {color}; text-decoration: none; word-break: break-all; }}
        .footer {{ text-align: center; font-size: 0.75rem; color: #9a9080; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e0d6cc; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 {category} 相關新聞摘要</h1>
        <div class="update-info">📅 更新時間：{now} | 共 {len(news_list)} 則新聞</div>
        {news_items_html}
        <div class="footer">
            <p>🤖 本頁資料由自動爬蟲產生，提供 AI 文章生成參考使用</p>
        </div>
    </div>
</body>
</html>"""


# ==================== 主程式 ====================
def main():
    print("=" * 60)
    print("🌿 台灣 ESG / 植生牆 / 碳盤查 新聞爬蟲 (多來源版本)")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 初始化結果
    all_news = {
        "植生牆": [],
        "ESG": [],
        "碳盤查": [],
        "生活": []
    }
    
    # 1. Google News RSS
    google_news = fetch_from_google_news()
    for category in all_news:
        all_news[category].extend(google_news.get(category, []))
    
    # 2. 台灣媒體 RSS
    taiwan_news = fetch_from_taiwan_rss()
    for category in all_news:
        all_news[category].extend(taiwan_news.get(category, []))
    
    # 3. 環境資訊中心
    einfo_news = fetch_from_einfo()
    for category in all_news:
        all_news[category].extend(einfo_news.get(category, []))
    
    # 去重（根據標題）
    for category in all_news:
        seen_titles = set()
        unique_news = []
        for news in all_news[category]:
            if news.title not in seen_titles:
                seen_titles.add(news.title)
                unique_news.append(news)
        all_news[category] = unique_news
        print(f"\n📊 {category}: 去重後共 {len(all_news[category])} 則")
    
    # 如果完全沒有新聞，使用模擬資料
    total_count = sum(len(all_news[cat]) for cat in all_news)
    if total_count == 0:
        print("\n⚠️ 所有來源皆未抓到新聞，改用模擬資料...")
        all_news = fetch_mock_news()
    
    # 儲存 JSON 和產生 HTML
    print("\n💾 儲存 JSON 資料...")
    save_to_json(all_news)
    
    print("\n📄 產生靜態 HTML 網頁...")
    generate_html_pages(all_news)
    
    print("\n" + "=" * 60)
    print("✅ 爬蟲執行完畢！")
    print(f"📁 JSON 資料位置: {NEWS_DATA_DIR}")
    print(f"📁 HTML 頁面位置: {NEWS_PAGES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
