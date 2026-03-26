from datetime import datetime

CATEGORIES = {
    "plant": {
        "name": "植物",
        "emoji": "🌱",
        "prompt": """
        請撰寫一篇關於植物的文章，主題可以包含：
        - 植物的養護技巧與知識
        - 植物的生態價值與文化意義
        - 適合室內種植的植物推薦
        - 植物與身心靈健康的關係
        
        文章風格：溫暖、親切、易讀，讓讀者感受到植物的療癒力量。
        長度：約400-600字。
        """,
        "image_prompt": "Beautiful plant in natural environment, soft lighting, nature photography style, 4k, highly detailed",
        "tags": ["植物", "園藝", "療癒", "生活美學"]
    },
    "carbon": {
        "name": "碳盤查",
        "emoji": "🌍",
        "prompt": """
        請撰寫一篇關於碳盤查的文章，主題可以包含：
        - 什麼是碳盤查與碳足跡
        - 企業如何進行碳盤查
        - 個人生活中如何減少碳足跡
        - 碳盤查的國際標準與趨勢
        
        文章風格：專業但易懂，數據佐證，實用性強。
        長度：約400-600字。
        """,
        "image_prompt": "Carbon footprint concept, green technology, sustainability, clean energy, infographic style, modern design",
        "tags": ["碳盤查", "碳足跡", "ESG", "永續發展"]
    },
    "sustainability": {
        "name": "永續",
        "emoji": "♻️",
        "prompt": """
        請撰寫一篇關於永續發展的文章，主題可以包含：
        - 永續生活的實踐方法
        - 循環經濟案例分享
        - 綠色消費與環保選擇
        - 全球永續趨勢與在地行動
        
        文章風格：積極正面，具體可行，啟發讀者行動。
        長度：約400-600字。
        """,
        "image_prompt": "Sustainable lifestyle, eco-friendly, green energy, circular economy, nature and technology harmony",
        "tags": ["永續", "環保", "循環經濟", "綠色生活"]
    },
    "life": {
        "name": "生活",
        "emoji": "✨",
        "prompt": """
        請撰寫一篇生活風格文章，主題可以包含：
        - 慢生活的實踐與哲學
        - 居家美學與空間整理
        - 心靈成長與自我照顧
        - 簡單生活中的幸福時刻
        
        文章風格：溫暖、療癒、有深度，引發共鳴。
        長度：約400-600字。
        """,
        "image_prompt": "Cozy lifestyle, peaceful home interior, warm atmosphere, mindfulness concept, aesthetic photography",
        "tags": ["生活風格", "慢生活", "心靈成長", "美學"]
    }
}

def get_today_category():
    """根據日期輪流選擇類別，確保四類循環發布"""
    days_since_epoch = datetime.now().toordinal()
    categories_list = list(CATEGORIES.keys())
    # 從2024年1月1日開始循環
    start_date = datetime(2024, 1, 1).toordinal()
    index = (days_since_epoch - start_date) % len(categories_list)
    return categories_list[index]
