import google.generativeai as genai
import re
from typing import Dict

class ArticleGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
    
    def generate(self, category_key: str, category_info: Dict) -> Dict:
        """使用 Gemini 生成文章（純知識庫模式）"""
        
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
- 不要使用 Markdown 語法（如 ** 或 ##）
"""
        
        try:
            model = genai.GenerativeModel('gemini-pro')
            
            print("🤖 正在呼叫 Gemini API 生成文章...")
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 2000,
                }
            )
            
            print(f"📡 Gemini 回應長度: {len(response.text)} 字元")
            
            article_data = self._parse_json_response(response.text)
            article_data = self._clean_markdown(article_data)
            
            from datetime import datetime
            article_data.update({
                "category": category_info["name"],
                "category_key": category_key,
                "tags": category_info.get("tags", []),
                "date": datetime.now().strftime("%Y年%m月%d日")
            })
            
            return article_data
            
        except Exception as e:
            print(f"❌ Gemini API 呼叫失敗: {e}")
            return self._get_fallback_article(category_info)
    
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
            title = article_data["title"]
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
            title = re.sub(r'^#+\s*', '', title)
            article_data["title"] = title.strip()
        
        if "summary" in article_data:
            summary = article_data["summary"]
            summary = re.sub(r'\*\*(.+?)\*\*', r'\1', summary)
            article_data["summary"] = summary.strip()
        
        if "key_points" in article_data and isinstance(article_data["key_points"], list):
            cleaned_points = []
            for point in article_data["key_points"]:
                point = re.sub(r'\*\*(.+?)\*\*', r'\1', point)
                cleaned_points.append(point.strip())
            article_data["key_points"] = cleaned_points
        
        if "content" in article_data:
            content = article_data["content"]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
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
            "tags": category_info.get("tags", []),
            "date": datetime.now().strftime("%Y年%m月%d日")
        }
