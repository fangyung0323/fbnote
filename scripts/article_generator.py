import json
import requests
import re
from typing import Dict

class ArticleGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
    
    def generate(self, category_key: str, category_info: Dict) -> Dict:
        """使用 DeepSeek 生成完整文章（碳盤查/永續類別會開啟聯網搜尋）"""
        
        # 判斷是否需要聯網搜尋
        search_categories = ["carbon", "sustainability"]  # 碳盤查 和 永續
        enable_search = category_key in search_categories
        
        print(f"🔍 聯網搜尋: {'開啟' if enable_search else '關閉'} (類別: {category_info['name']})")
        
        system_prompt = """
你是一個專業的內容創作者，專門為「蕨積」網站撰寫高品質文章。
請以JSON格式輸出，包含以下欄位：
- title: 吸引人的文章標題（15字以內）
- summary: 一句話總結（30字以內）
- key_points: 三個重點，格式為 ["重點一", "重點二", "重點三"]
- content: 文章內文，使用HTML格式，包含適當的<h2>、<p>標籤
- reading_time: 閱讀時間（分鐘）

內文格式要求：
- 至少3個小節（用<h2>標示）
- 每個小節至少2個段落
- 適當使用列表或重點整理
- 結尾要有總結或行動呼籲

重要規則：
1. summary 和 key_points 必須完全從文章內容提煉，不要憑空捏造
2. title 欄位只能有純文字標題，不要加任何符號
3. content 欄位只能使用 HTML 標籤，不要使用 Markdown 語法
4. 不要輸出JSON以外的任何文字
"""
        
        if enable_search:
            user_prompt = f"""
類別：{category_info['name']} {category_info['emoji']}
寫作要求：{category_info['prompt']}

【特別要求】
請先使用聯網搜尋功能，查詢近一週內與「{category_info['name']}」相關的最新新聞、政策、企業案例或研究報告。
然後根據搜尋結果，結合你的知識，撰寫一篇有深度、有時效性的文章。

請生成一篇符合該類別風格的文章，並同時產生摘要和重點。
"""
        else:
            user_prompt = f"""
類別：{category_info['name']} {category_info['emoji']}
寫作要求：{category_info['prompt']}

請生成一篇符合該類別風格的文章，並同時產生摘要和重點。
"""
        
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "enable_search": enable_search
                },
                timeout=90
            )
            
            result = response.json()
            article_data = json.loads(result["choices"][0]["message"]["content"])
            
            # 二次清理：確保沒有任何 Markdown 殘留
            article_data = self._clean_markdown(article_data)
            
            # 添加後設資料
            from datetime import datetime
            article_data.update({
                "category": category_info["name"],
                "category_key": category_key,
                "tags": category_info["tags"],
                "date": datetime.now().strftime("%Y年%m月%d日")
            })
            
            return article_data
            
        except Exception as e:
            print(f"❌ 文章生成失敗: {e}")
            return self._get_fallback_article(category_info)
    
    def _clean_markdown(self, article_data: Dict) -> Dict:
        """二次清理：移除任何殘留的 Markdown 語法"""
        
        # 清理 title
        if "title" in article_data:
            title = article_data["title"]
            title = re.sub(r'^標題[:：]\s*', '', title)
            title = re.sub(r'^#+\s*', '', title)
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
            article_data["title"] = title.strip()
        
        # 清理 summary
        if "summary" in article_data:
            summary = article_data["summary"]
            summary = re.sub(r'\*\*(.+?)\*\*', r'\1', summary)
            summary = re.sub(r'^#+\s*', '', summary)
            article_data["summary"] = summary.strip()
        
        # 清理 key_points
        if "key_points" in article_data and isinstance(article_data["key_points"], list):
            cleaned_points = []
            for point in article_data["key_points"]:
                point = re.sub(r'\*\*(.+?)\*\*', r'\1', point)
                point = re.sub(r'^#+\s*', '', point)
                cleaned_points.append(point.strip())
            article_data["key_points"] = cleaned_points
        
        # 清理 content
        if "content" in article_data:
            content = article_data["content"]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
            content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
            content = re.sub(r'^---+$', '', content, flags=re.MULTILINE)
            article_data["content"] = content
        
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
            "tags": category_info["tags"],
            "date": datetime.now().strftime("%Y年%m月%d日")
        }
