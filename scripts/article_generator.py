import json
import requests
from typing import Dict

class ArticleGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
    
    def generate(self, category_key: str, category_info: Dict) -> Dict:
        """使用 DeepSeek 生成完整文章"""
        
        system_prompt = """
        你是一個專業的內容創作者，專門為「蕨積」網站撰寫高品質文章。
        請以JSON格式輸出，包含以下欄位：
        - title: 吸引人的文章標題（15字以內）
        - summary: 文章摘要（100字以內）
        - content: 文章內文，使用HTML格式，包含適當的<h2>、<p>標籤
        - reading_time: 閱讀時間（分鐘）
        
        內文格式要求：
        - 至少3個小節（用<h2>標示）
        - 每個小節至少2個段落
        - 適當使用列表或重點整理
        - 結尾要有總結或行動呼籲
        """
        
        user_prompt = f"""
        類別：{category_info['name']} {category_info['emoji']}
        寫作要求：{category_info['prompt']}
        
        請生成一篇符合該類別風格的文章。
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
                    "temperature": 0.8,
                    "response_format": {"type": "json_object"}
                },
                timeout=60
            )
            
            result = response.json()
            article_data = json.loads(result["choices"][0]["message"]["content"])
            
            # 添加後設資料
            article_data.update({
                "category": category_info["name"],
                "category_key": category_key,
                "tags": category_info["tags"],
                "date": self._get_current_date()
            })
            
            return article_data
            
        except Exception as e:
            print(f"文章生成失敗: {e}")
            return self._get_fallback_article(category_info)
    
    def _get_current_date(self):
        from datetime import datetime
        return datetime.now().strftime("%Y年%m月%d日")
    
    def _get_fallback_article(self, category_info):
        """備用文章（當API失敗時）"""
        return {
            "title": f"{category_info['name']}的日常美好",
            "summary": f"探索{category_info['name']}的世界，發現生活中的美好。",
            "content": f"<h2>關於{category_info['name']}</h2><p>今天讓我們一起探索{category_info['name']}的美好。在這個快速變化的時代，{category_info['name']}為我們帶來平靜與啟發。</p>",
            "reading_time": 3,
            "category": category_info["name"],
            "category_key": "fallback",
            "tags": category_info["tags"],
            "date": self._get_current_date()
        }
