import requests
import base64
import os

class ImageGenerator:
    def __init__(self, api_key: str, service: str = "deepseek"):
        self.api_key = api_key
        self.service = service
        
        # 目前 DeepSeek 尚未提供圖片生成，建議使用 Replicate 或 Pollinations.ai
        # 這裡使用免費的 Pollinations.ai 作為示範
        self.image_api_url = "https://image.pollinations.ai/prompt/"
    
    def generate(self, prompt: str, category_key: str) -> str:
        """生成圖片並儲存，回傳圖片路徑"""
        
        # 優化提示詞
        enhanced_prompt = f"{prompt}, website article header, high quality, 16:9 aspect ratio"
        
        try:
            # 方法一：使用 Pollinations.ai（免費，無需API Key）
            image_url = f"{self.image_api_url}{enhanced_prompt}"
            
            # 下載圖片
            response = requests.get(image_url, timeout=30)
            
            # 儲存圖片
            filename = f"{category_key}_{self._get_date_string()}.jpg"
            filepath = f"images/{filename}"
            os.makedirs("images", exist_ok=True)
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            return f"/images/{filename}"
            
        except Exception as e:
            print(f"圖片生成失敗: {e}")
            return "/images/default.jpg"
    
    def _get_date_string(self):
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d")
