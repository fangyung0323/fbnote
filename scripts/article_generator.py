import google.generativeai as genai
import feedparser
import requests
import re
from typing import Dict, Optional
from bs4 import BeautifulSoup

class ArticleGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
    
    # ==================== RSS 新聞來源 ====================
    RSS_SOURCES = {
        "sustainability": [
            "https://e-info.org.tw/rss.xml",  # 環境資訊中心
            "https://csrone.com/rss",          # CSRone 永續智庫
            "https://www.cna.com.tw/topic/rss/4361",  # 中央社淨零碳排
        ],
        "carbon": [
            "https://e-info.org.tw/rss.xml",  # 環境資訊中心
            "https://csrone.com/rss",          # CSRone 永續智庫
        ]
    }
    
    def fetch_latest_news(self, category_key: str) -> Optional[Dict]:
        """從 RSS 抓取最新一篇新聞"""
        rss_urls = self.RSS_SOURCES.get(category_key, [])
        
        for rss_url in rss_urls:
            try:
                print(f"📡 嘗試讀取 RSS: {rss_url}")
                feed = feedparser.parse(rss_url)
                
                if feed.entries and len(feed.entries) > 0:
                    latest = feed.entries[0]
                    
                    # 嘗試取得完整內文
                    content = self._fetch_article_content(latest.link)
                    
                    if content:
                        print(f"✅ 找到新聞: {latest.title}")
                        return {
                            "title": latest.title,
                            "link": latest.link,
                            "summary": latest.get("summary", ""),
                            "content": content,
                            "published": latest.get("published", "")
                        }
            except Exception as e:
                print(f"⚠️ RSS 讀取失敗: {e}")
                continue
        
        print("❌ 沒有找到可用的新聞")
        return None
    
    def _fetch_article_content(self, url: str) -> Optional[str]:
        """抓取新聞網頁的完整內文"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除 script 和 style 標籤
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 嘗試常見的內文容器
            content_selectors = [
                'article', '.article-content', '.post-content', 
                '.entry-content', '.content', '#main-content'
            ]
            
            content_text = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content_text = elements[0].get_text()
                    break
            
            if not content_text:
                content_text = soup.get_text()
            
            # 清理文字
            lines = (line.strip() for line in content_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content_text = ' '.join(chunk for chunk in chunks if chunk)
            
            # 限制長度（避免超過 token 限制）
            content_text = content_text[:6000]
            
            return content_text if len(content_text) > 200 else None
            
        except Exception as e:
            print(f"⚠️ 抓取文章內容失敗: {e}")
            return None
    
    def generate_with_news(self, category_key: str, category_info: Dict, news: Dict) -> Dict:
        """使用新聞內容生成文章"""
        print(f"📰 使用新聞改寫: {news['title']}")
        
        prompt = f"""
你是「蕨積」網站的專業內容創作者，擅長撰寫科普與生活風格文章。

【參考資料】
請根據以下新聞內容，改寫成一篇適合網站發布的科普文章。

新聞標題：{news['title']}
新聞來源：{news['link']}
新聞日期：{news.get('published', '未知')}
新聞內容：
{news['content'][:4000]}

【輸出格式】
請嚴格按照以下 JSON 格式輸出，不要輸出其他內容：
{{
  "title": "改寫後的吸引人標題（15字以內）",
  "summary": "一句話總結（30字以內）",
  "key_points": ["重點一", "重點二", "重點三"],
  "content": "完整文章內容，使用 HTML 格式，包含 <h2>、<p> 標籤",
  "reading_time": 3
}}

【要求】
- 語言使用繁體中文
- 文章長度約 500-800 字
- 結尾加上「🌿 蕨積 - 讓生活多一點綠」
- 不要直接複製貼上，要用自己的話改寫
- 如果可以，請在新聞結尾附上引用來源
"""
        return self._call_gemini(prompt, category_info)
    
    def generate_without_news(self, category_key: str, category_info: Dict) -> Dict:
        """沒有新聞時，使用 AI 知識庫生成文章"""
        print(f"📚 使用知識庫生成文章 (類別: {category_info['name']})")
        
        prompt = f"""
你是「蕨積」網站的專業內容創作者，擅長撰寫科普與生活風格文章。

【任務】
請撰寫一篇關於「{category_info['name']}」的科普或生活文章。

{category_info['prompt']}

【輸出格式】
請嚴格按照以下 JSON 格式輸出，不要輸出其他內容：
{{
  "title": "吸引人的文章標題（15字以內）",
  "summary": "一句話總結（30字以內）",
  "key_points": ["重點一", "重點二", "重點三"],
  "content": "完整文章內容，使用 HTML 格式，包含 <h2>、<p> 標籤",
  "reading_time": 3
}}

【要求】
- 文章長度約 500-800 字
- 語言使用繁體中文
- 結尾加上「🌿 蕨積 - 讓生活多一點綠」
- 摘要和重點必須從文章內容提煉
"""
        return self._call_gemini(prompt, category_info)
    
   def _call_gemini(self, prompt: str, category_info: Dict) -> Dict:
    """呼叫 Gemini API 並解析回傳"""
    try:
        # 使用 gemini-pro 模型
        model = genai.GenerativeModel('gemini-pro')
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2000,
            }
        )
        
        article_data = self._parse_json_response(response.text)
        article_data = self._clean_markdown(article_data)
        
        return article_data
        
    except Exception as e:
        print(f"❌ Gemini API 呼叫失敗: {e}")
        return self._get_fallback_article(category_info)
    
    def generate(self, category_key: str, category_info: Dict) -> Dict:
        """主要生成函數：先嘗試抓新聞，沒新聞就用知識庫"""
        
        # 判斷是否需要嘗試抓新聞（碳盤查、永續）
        search_categories = ["carbon", "sustainability"]
        should_fetch_news = category_key in search_categories
        
        if should_fetch_news:
            print(f"🔍 嘗試從 RSS 抓取最新新聞...")
            news = self.fetch_latest_news(category_key)
            
            if news:
                return self.generate_with_news(category_key, category_info, news)
            else:
                print(f"⚠️ 沒有找到新聞，改用知識庫生成")
                return self.generate_without_news(category_key, category_info)
        else:
            # 植物、生活類別直接用知識庫
            return self.generate_without_news(category_key, category_info)
    
    def _parse_json_response(self, text: str) -> Dict:
        """從 Gemini 回應中解析 JSON"""
        try:
            import json
            return json.loads(text)
        except:
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                import json
                return json.loads(json_match.group())
            else:
                return {
                    "title": "未知標題",
                    "summary": "無法解析文章摘要",
                    "key_points": ["無法提取重點"],
                    "content": text,
                    "reading_time": 3
                }
    
    def _clean_markdown(self, article_data: Dict) -> Dict:
        """清理 Markdown 語法"""
        if "title" in article_data:
            article_data["title"] = re.sub(r'\*\*(.+?)\*\*', r'\1', article_data["title"])
            article_data["title"] = re.sub(r'^#+\s*', '', article_data["title"])
            article_data["title"] = article_data["title"].strip()
        
        if "summary" in article_data:
            article_data["summary"] = re.sub(r'\*\*(.+?)\*\*', r'\1', article_data["summary"])
            article_data["summary"] = article_data["summary"].strip()
        
        if "key_points" in article_data and isinstance(article_data["key_points"], list):
            cleaned = [re.sub(r'\*\*(.+?)\*\*', r'\1', p).strip() for p in article_data["key_points"]]
            article_data["key_points"] = cleaned
        
        if "content" in article_data:
            article_data["content"] = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', article_data["content"])
            article_data["content"] = re.sub(r'\*(.+?)\*', r'<em>\1</em>', article_data["content"])
        
        return article_data
    
    def _get_fallback_article(self, category_info: Dict) -> Dict:
        """備用文章（當 API 失敗時）"""
        from datetime import datetime
        
        return {
            "title": f"{category_info['name']}的日常美好",
            "summary": f"探索{category_info['name']}的世界，發現生活中的美好。",
            "key_points": ["觀點一", "觀點二", "觀點三"],
            "content": f"<h2>關於{category_info['name']}</h2><p>今天讓我們一起探索{category_info['name']}的美好。在這個快速變化的時代，{category_info['name']}為我們帶來平靜與啟發。</p><h2>為什麼要關注{category_info['name']}</h2><p>因為它與我們的日常生活息息相關，值得我們深入了解。</p><p>結語：讓我們一起持續學習與成長！</p>",
            "reading_time": 3,
            "category": category_info["name"],
            "category_key": "fallback",
            "tags": category_info.get("tags", []),
            "date": datetime.now().strftime("%Y年%m月%d日")
        }
