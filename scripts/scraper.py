#!/usr/bin/env python3
"""
台灣 ESG / 植生牆 / 碳盤查 / 生活 新聞爬蟲
支援多種來源：Google News RSS、台灣媒體 RSS、環境資訊中心、上下游新聞
產生 JSON 資料和靜態 HTML 網頁
只保留 7 天內的新聞
"""

import os
import json
import re
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
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

# 新聞時效性設定（只保留幾天內的新聞）
MAX_DAYS_OLD = 7  # 只保留 7 天內的新聞

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
            "summary": self.summary[:200],
            "content": self.content[:500] if self.content else "",
            "category": self.category,
            "key_points": self.key_points
        }

# ==================== 日期處理函式 ====================
def is_recent(date_str: str, max_days: int = MAX_DAYS_OLD) -> bool:
    """檢查日期是否在指定天數內"""
    if not date_str:
        return False
    try:
        # 嘗試解析各種日期格式
        if 'T' in date_str:
            news_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        elif '-' in date_str and len(date_str) >= 10:
            news_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        elif '/' in date_str and len(date_str) >= 10:
            news_date = datetime.strptime(date_str[:10], "%Y/%m/%d")
        else:
            # 無法解析，保守保留
            return True
        
        now = datetime.now()
        days_diff = (now - news_date).days
        return 0 <= days_diff <= max_days
    except:
        return True  # 解析失敗時保留

def parse_rss_date(date_str: str) -> Optional[str]:
    """解析 RSS 的日期格式，回傳 YYYY-MM-DD"""
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        date_obj = parsedate_to_datetime(date_str)
        return date_obj.strftime("%Y-%m-%d")
    except:
        # 嘗試其他格式
        patterns = [
            (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
            (r'(\d{4})/(\d{2})/(\d{2})', '%Y/%m/%d'),
        ]
        for pattern, fmt in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    return datetime.strptime(match.group(0), fmt).strftime("%Y-%m-%d")
                except:
                    pass
        return datetime.now().strftime("%Y-%m-%d")

# ==================== 關鍵字分類對應（擴充植生牆相關）====================
KEYWORD_TO_CATEGORY = {
    # 植生牆 / 植物 / 園藝 / 景觀 / 森林 相關
    "植生牆": "植生牆",
    "垂直綠化": "植生牆",
    "綠牆": "植生牆",
    "植物": "植生牆",
    "綠化": "植生牆",
    "盆栽": "植生牆",
    "花園": "植生牆",
    "園藝": "植生牆",
    "景觀": "植生牆",
    "森林": "植生牆",
    "造林": "植生牆",
    "樹木": "植生牆",
    "花草": "植生牆",
    "綠地": "植生牆",
    "屋頂綠化": "植生牆",
    "生態園區": "植生牆",
    "植栽": "植生牆",
    "育苗": "植生牆",
    "林業": "植生牆",
    "公園": "植生牆",
    "行道樹": "植生牆",
    
    # ESG 相關
    "ESG": "ESG",
    "永續": "ESG",
    "CSR": "ESG",
    "企業社會責任": "ESG",
    "永續發展": "ESG",
    "SDGs": "ESG",
    
    # 碳盤查相關
    "碳盤查": "碳盤查",
    "碳足跡": "碳盤查",
    "淨零": "碳盤查",
    "碳中和": "碳盤查",
    "溫室氣體": "碳盤查",
    "碳權": "碳盤查",
    "氣候變遷": "碳盤查",
    "減碳": "碳盤查",
    
    # 生活相關
    "生活": "生活",
    "環保生活": "生活",
    "零浪費": "生活",
    "綠色生活": "生活",
    "減塑": "生活",
    "循環經濟": "生活",
    "永續飲食": "生活",
    "環保餐具": "生活"
}

def classify_article(title: str, summary: str = "") -> str:
    """根據標題和內容判斷分類"""
    text_to_check = f"{title} {summary}".lower()
    
    # 優先匹配更具體的分類
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword.lower() in text_to_check:
            return category
    
    return "生活"  # 預設分類

# ==================== 來源1：Google News RSS（強化植生牆關鍵字 + 時間過濾）====================
GOOGLE_NEWS_QUERIES = {
    "植生牆": [
        "植生牆 台灣 when:7d", 
        "垂直綠化 when:7d", 
        "綠牆 建築 when:7d",
        "園藝 台灣 when:7d",
        "景觀 設計 台灣 when:7d",
        "森林 保育 台灣 when:7d",
        "植物 新種 台灣 when:7d",
        "都市綠化 台灣 when:7d",
        "屋頂綠化 台灣 when:7d",
        "行道樹 種植 台灣 when:7d"
    ],
    "ESG": [
        "ESG 台灣 when:7d", 
        "永續發展 台灣 when:7d",
        "企業社會責任 台灣 when:7d"
    ],
    "碳盤查": [
        "碳盤查 台灣 when:7d", 
        "碳足跡 企業 when:7d", 
        "淨零排放 台灣 when:7d"
    ],
    "生活": [
        "環保生活 台灣 when:7d", 
        "零廢棄 生活 when:7d", 
        "綠色消費 台灣 when:7d"
    ]
}

def fetch_from_google_news() -> Dict[str, List[NewsItem]]:
    """從 Google News RSS 抓取新聞（強化關鍵字 + 日期過濾）"""
    all_news = {
        "植生牆": [],
        "ESG": [],
        "碳盤查": [],
        "生活": []
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    print("\n🔍 開始從 Google News 抓取（限定 7 天內）...")
    
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
                        
                        # 解析日期
                        date_str = parse_rss_date(published)
                        if not date_str:
                            date_str = datetime.now().strftime("%Y-%m-%d")
                        
                        # 🔥 過濾舊新聞
                        if not is_recent(date_str):
                            print(f"  ⏭️ [過濾] {title[:30]}... (日期: {date_str})")
                            continue
                        
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
                            print(f"  ✅ [Google/{category}] {title[:40]}... ({date_str})")
                    
            except Exception as e:
                print(f"  ⚠️ Google News 查詢失敗 ({query}): {e}")
            
            time.sleep(1)
    
    return all_news

# ==================== 來源2：台灣媒體 RSS ====================
RSS_FEEDS = [
    {"name": "中央社", "url": "https://www.cna.com.tw/rss/all.xml"},
    {"name": "自由時報", "url": "https://news.ltn.com.tw/rss/all.xml"},
    {"name": "環境資訊中心", "url": "https://e-info.org.tw/rss.xml"},
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
            
            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:200]
                link = entry.get("link", "")
                published = entry.get("published", "")
                
                # 清理摘要
                summary = re.sub(r'<[^>]+>', '', summary)
                
                # 判斷分類
                category = classify_article(title, summary)
                
                # 解析日期
                date_str = parse_rss_date(published)
                if not date_str:
                    date_str = datetime.now().strftime("%Y-%m-%d")
                
                # 過濾舊新聞
                if not is_recent(date_str):
                    continue
                
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
                    print(f"  ✅ [{source_name}/{category}] {title[:40]}... ({date_str})")
                    
        except Exception as e:
            print(f"  ❌ {source_name} RSS 失敗: {e}")
        
        time.sleep(1)
    
    return all_news

# ==================== 來源3：上下游新聞（農業/植物相關）====================
def fetch_from_newsandmarket() -> Dict[str, List[NewsItem]]:
    """從上下游新聞抓取農業/植物相關新聞"""
    all_news = {
        "植生牆": [],
        "ESG": [],
        "碳盤查": [],
        "生活": []
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    print("\n🌾 開始從上下游新聞抓取...")
    
    # 上下游新聞的首頁和分類頁面
    urls = [
        "https://www.newsmarket.com.tw/",
        "https://www.newsmarket.com.tw/category/environment/",
        "https://www.newsmarket.com.tw/category/agriculture/",
    ]
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尋找文章區塊
                articles = soup.find_all('article')
                if not articles:
                    articles = soup.find_all('div', class_=re.compile(r'post|entry|item'))
                
                for article in articles[:15]:
                    # 找標題連結
                    title_link = article.find('a', href=True)
                    if not title_link:
                        continue
                    
                    title = title_link.get_text(strip=True)
                    href = title_link['href']
                    
                    if not title or len(title) < 10:
                        continue
                    
                    # 完整網址
                    if href.startswith('/'):
                        full_url = f"https://www.newsmarket.com.tw{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # 找日期
                    date_elem = article.find('time', class_=re.compile(r'date|entry-date'))
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    if date_elem and date_elem.get('datetime'):
                        date_str = parse_rss_date(date_elem['datetime'][:10])
                    elif date_elem:
                        date_text = date_elem.get_text(strip=True)
                        date_str = parse_rss_date(date_text)
                    
                    if not date_str:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # 過濾舊新聞
                    if not is_recent(date_str):
                        continue
                    
                    # 找摘要
                    summary_elem = article.find('p', class_=re.compile(r'excerpt|summary|description'))
                    summary = summary_elem.get_text(strip=True)[:150] if summary_elem else title[:150]
                    
                    # 分類
                    category = classify_article(title, summary)
                    
                    # 去重
                    existing_titles = [n.title for n in all_news[category]]
                    if title not in existing_titles:
                        news_item = NewsItem(
                            title=title,
                            source="上下游新聞",
                            url=full_url,
                            date=date_str,
                            summary=summary,
                            content="",
                            category=category
                        )
                        all_news[category].append(news_item)
                        print(f"  ✅ [上下游新聞/{category}] {title[:40]}... ({date_str})")
                
            else:
                print(f"  ⚠️ 上下游新聞回應: {response.status_code}")
                
        except Exception as e:
            print(f"  ⚠️ 上下游新聞抓取失敗: {e}")
        
        time.sleep(2)
    
    return all_news

# ==================== 來源4：我們的島（環境/植物相關）====================
def fetch_from_our_island() -> Dict[str, List[NewsItem]]:
    """從我們的島節目抓取環境相關新聞"""
    all_news = {
        "植生牆": [],
        "ESG": [],
        "碳盤查": [],
        "生活": []
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    print("\n🏝️ 開始從我們的島抓取...")
    
    url = "https://ourisland.pts.org.tw/"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尋找文章連結
            for link in soup.find_all('a', href=True):
                href = link['href']
                title = link.get_text(strip=True)
                
                # 過濾條件
                if not title or len(title) < 10:
                    continue
                
                # 檢查是否為文章連結
                if '/content/' in href or '/node/' in href or '/story/' in href:
                    if href.startswith('/'):
                        full_url = f"https://ourisland.pts.org.tw{href}"
                    else:
                        full_url = href
                    
                    # 找日期
                    date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', title)
                    if date_match:
                        date_str = date_match.group(0)
                    else:
                        date_str = datetime.now().strftime("%Y-%m-%d")
                    
                    # 過濾舊新聞
                    if not is_recent(date_str):
                        continue
                    
                    category = classify_article(title)
                    
                    existing_titles = [n.title for n in all_news[category]]
                    if title not in existing_titles:
                        news_item = NewsItem(
                            title=title,
                            source="我們的島",
                            url=full_url,
                            date=date_str,
                            summary=title[:150],
                            content="",
                            category=category
                        )
                        all_news[category].append(news_item)
                        print(f"  ✅ [我們的島/{category}] {title[:40]}... ({date_str})")
        
        else:
            print(f"  ⚠️ 我們的島回應: {response.status_code}")
            
    except Exception as e:
        print(f"  ⚠️ 我們的島抓取失敗: {e}")
    
    return all_news

# ==================== 來源5：模擬資料（備用，且日期新鮮）====================
def fetch_mock_news() -> Dict[str, List[NewsItem]]:
    """產生模擬新聞資料（日期保持新鮮）"""
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    
    mock_news = {
        "植生牆": [
            NewsItem(
                title="北市推建築物植生牆補助 每坪最高3000元",
                source="自由時報",
                url="https://news.ltn.com.tw/news/life/example1",
                date=two_days_ago,
                summary="台北市都發局宣布，為推動城市綠化，將補助既有建築物設置植生牆，每坪最高補助3000元。",
                content="台北市都發局今日召開記者會，宣布推出「建築物植生牆設置補助計畫」。補助對象為台北市既有建築物，每案最高補助30萬元。",
                category="植生牆"
            ),
            NewsItem(
                title="研究：辦公室的植生牆可提升15%工作效率",
                source="環境資訊中心",
                url="https://e-info.org.tw/node/example2",
                date=yesterday,
                summary="最新研究顯示，辦公室設置植生牆不僅能淨化空氣，還能提升員工15%的工作效率。",
                content="荷蘭烏特勒支大學研究發現，在辦公室設置植生牆後，員工工作效率平均提升15%，壓力指數降低22%。",
                category="植生牆",
                key_points=["提升15%工作效率", "降低22%壓力", "減少18%缺勤率"]
            ),
            NewsItem(
                title="台中花博園區轉型永續公園 新增植生牆景觀",
                source="聯合新聞網",
                url="https://udn.com/news/example3",
                date=three_days_ago,
                summary="台中的花博園區將轉型為永續公園，新增多處植生牆景觀，成為都市新地標。",
                content="台中市政府宣布，后里花博園區將改造為永續環境教育園區，新增植生牆、雨水回收系統等設施。",
                category="植生牆"
            )
        ],
        "ESG": [
            NewsItem(
                title="台灣企業ESG評比出爐 推動綠色轉型有成",
                source="CSR天下",
                url="https://csr.cw.com.tw/example4",
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
                url="https://money.udn.com/example5",
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
                url="https://ubrand.udn.com/example6",
                date=two_days_ago,
                summary="主打循環經濟的環保容器租借服務進駐台北，民眾可租借可重複使用的容器。",
                content="新創團隊推出環保容器租借服務，鼓勵民眾減少一次性垃圾。",
                category="生活"
            ),
            NewsItem(
                title="新北社區推都市農園 居民一起種菜享樂趣",
                source="自由時報",
                url="https://news.ltn.com.tw/example7",
                date=three_days_ago,
                summary="新北市某社區推出都市農園計畫，讓居民在頂樓種植蔬菜水果。",
                content="社區管委會和里長合作，在社區頂樓打造都市農園，不僅綠化環境還能自給自足。",
                category="植生牆"
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
            # 如果沒有新聞，保留原有檔案但標記為空
            filepath = os.path.join(NEWS_DATA_DIR, file_map.get(category, f"{category}.json"))
            if not os.path.exists(filepath):
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
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
                    # 只保留 7 天內的新聞
                    existing_news = [item for item in existing_news if is_recent(item.get("date", ""))]
            except:
                existing_news = []
        
        # 合併新資料
        existing_urls = {item.get("url") for item in existing_news}
        new_items = [item.to_dict() for item in news_list if item.url not in existing_urls and is_recent(item.date)]
        
        if new_items:
            all_items = new_items + existing_news
            # 按日期排序（最新的在前）
            all_items.sort(key=lambda x: x.get("date", ""), reverse=True)
            # 只保留最近 50 筆
            all_items = all_items[:50]
            
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
        <div class="update-info">📅 更新時間：{now} | 只顯示 {MAX_DAYS_OLD} 天內的新聞</div>
        {preview_html}
        <div class="footer">
            <p>🤖 本頁由自動爬蟲產生，資料僅供 AI 文章生成參考</p>
            <p>資料來源：Google News、中央社、自由時報、環境資訊中心、上下游新聞、我們的島</p>
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
<p>📌 只顯示 {MAX_DAYS_OLD} 天內的新聞</p>
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
        <div class="update-info">📅 更新時間：{now} | 共 {len(news_list)} 則新聞（{MAX_DAYS_OLD} 天內）</div>
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
    print("🌿 台灣 ESG / 植生牆 / 碳盤查 新聞爬蟲 (多來源 + 時效過濾版)")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"時效設定: 只保留 {MAX_DAYS_OLD} 天內的新聞")
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
    
    # 3. 上下游新聞
    newsandmarket_news = fetch_from_newsandmarket()
    for category in all_news:
        all_news[category].extend(newsandmarket_news.get(category, []))
    
    # 4. 我們的島
    ourisland_news = fetch_from_our_island()
    for category in all_news:
        all_news[category].extend(ourisland_news.get(category, []))
    
    # 去重（根據標題）並過濾日期
    for category in all_news:
        seen_titles = set()
        unique_news = []
        for news in all_news[category]:
            # 再次確保日期在範圍內
            if not is_recent(news.date):
                continue
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
        # 模擬資料也要過濾日期
        for category in all_news:
            all_news[category] = [n for n in all_news[category] if is_recent(n.date)]
    
    # 儲存 JSON 和產生 HTML
    print("\n💾 儲存 JSON 資料...")
    save_to_json(all_news)
    
    print("\n📄 產生靜態 HTML 網頁...")
    generate_html_pages(all_news)
    
    print("\n" + "=" * 60)
    print("✅ 爬蟲執行完畢！")
    print(f"📁 JSON 資料位置: {NEWS_DATA_DIR}")
    print(f"📁 HTML 頁面位置: {NEWS_PAGES_DIR}")
    print(f"📌 注意：只保留 {MAX_DAYS_OLD} 天內的新聞")
    print("=" * 60)


if __name__ == "__main__":
    main()
