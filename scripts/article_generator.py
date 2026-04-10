import json
import requests
import re
from typing import Dict

class ArticleGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
    
    def generate(self, category_key: str, category_info: Dict) -> Dict:
        """使用 DeepSeek 生成完整文章，確保輸出純 HTML，無 Markdown"""
        
        system_prompt = """
你是一個專業的內容創作者，專門為「蕨積」網站撰寫高品質文章。

【重要格式規則】
請以 JSON 格式輸出，包含以下欄位：
- title: 文章標題（15字以內，純文字，不要加任何符號）
- summary: 文章摘要（100字以內，純文字）
- content: 文章內文，使用 HTML 格式
- reading_time: 閱讀時間（整數，單位：分鐘）

【content 欄位的 HTML 規範】
✅ 正確示範：
<h2>第一節標題</h2>
<p>這是一個段落，包含有意義的內容。</p>
<p>這是另一個段落。</p>
<ul><li>重點項目一</li><li>重點項目二</li></ul>

❌ 絕對不要使用的語法：
- 不要使用 ## 或 ### 或 #### 當作標題
- 不要使用 **文字** 或 *文字* 當作粗體或斜體
- 不要使用 --- 或 *** 當作分隔線
- 不要使用 [連結](url) 這種 Markdown 連結語法
- 不要使用 > 當作引用

【content 內容要求】
- 至少 3 個小節（用 <h2> 標示）
- 每個小節至少 2 個段落（用 <p> 標示）
- 適當使用 <ul> 或 <ol> 列表整理重點
- 結尾要有總結或行動呼籲（用 <p> 標示）
- 全文約 600-800 字

【輸出範例】
{
  "title": "室內植物這樣養",
  "summary": "五種最適合新手的室內植物，以及養護技巧",
  "content": "<h2>為什麼植物能療癒人心</h2><p>研究顯示，室內植物能降低壓力...</p><h2>五種新手必備植物</h2><p>第一種是虎尾蘭...</p><ul><li>虎尾蘭：耐旱好養</li><li>黃金葛：適應力強</li></ul><h2>養護三大關鍵</h2><p>光照、澆水、通風...</p><p>結語：開始你的植感生活吧！</p>",
  "reading_time": 4
}

請嚴格遵守以上格式，不要輸出 JSON 以外的任何文字。
"""
        
        user_prompt = f"""
類別：{category_info['name']} {category_info['emoji']}
寫作要求：{category_info['prompt']}

請生成一篇符合該類別風格的文章，嚴格遵守 HTML 格式規範。
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
                    "response_format": {"type": "json_object"}
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
            # 移除「標題：」前綴
            title = re.sub(r'^標題[:：]\s*', '', title)
            # 移除開頭的 # 號
            title = re.sub(r'^#+\s*', '', title)
            # 移除粗體標記
            title = re.sub(r'\*\*(.+?)\*\*', r'\1', title)
            article_data["title"] = title.strip()
        
        # 清理 summary
        if "summary" in article_data:
            summary = article_data["summary"]
            summary = re.sub(r'\*\*(.+?)\*\*', r'\1', summary)
            summary = re.sub(r'^#+\s*', '', summary)
            article_data["summary"] = summary.strip()
        
        # 清理 content：將 Markdown 標題轉為 HTML
        if "content" in article_data:
            content = article_data["content"]
            
            # 將 ### 標題轉為 <h3>
            content = re.sub(r'^###\s+(.+?)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
            # 將 ## 標題轉為 <h2>
            content = re.sub(r'^##\s+(.+?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
            # 將 # 標題轉為 <h2>
            content = re.sub(r'^#\s+(.+?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
            
            # 移除粗體標記
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            # 移除斜體標記
            content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
            
            # 移除分隔線
            content = re.sub(r'^---+$', '', content, flags=re.MULTILINE)
            
            # 確保段落用 <p> 包裹（如果沒有）
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 如果已經是 HTML 標籤，保留
                if line.startswith('<h') or line.startswith('<p') or line.startswith('<ul') or line.startswith('<ol') or line.startswith('<li') or line.startswith('<strong') or line.startswith('<em'):
                    cleaned_lines.append(line)
                else:
                    # 否則用 <p> 包裹
                    cleaned_lines.append(f'<p>{line}</p>')
            
            article_data["content"] = '\n'.join(cleaned_lines)
        
        return article_data
    
    def _get_fallback_article(self, category_info: Dict) -> Dict:
        """備用文章（當 API 失敗時）"""
        from datetime import datetime
        
        return {
            "title": f"{category_info['name']}的日常美好",
            "summary": f"探索{category_info['name']}的世界，發現生活中的美好。",
            "content": f"<h2>關於{category_info['name']}</h2><p>今天讓我們一起探索{category_info['name']}的美好。在這個快速變化的時代，{category_info['name']}為我們帶來平靜與啟發。</p><h2>為什麼要關注{category_info['name']}</h2><p>因為它與我們的日常生活息息相關，值得我們深入了解。</p><p>結語：讓我們一起持續學習與成長！</p>",
            "reading_time": 3,
            "category": category_info["name"],
            "category_key": "fallback",
            "tags": category_info["tags"],
            "date": datetime.now().strftime("%Y年%m月%d日")
        }
