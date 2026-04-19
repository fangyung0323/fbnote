#!/usr/bin/env python3
"""
每日摘要寄送機器人
- 從 Google Sheet 讀取訂閱者名單
- 從文章 HTML 中讀取預存的摘要（不再呼叫 AI）
- 透過 Gmail SMTP 寄送
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==================== 讀取環境變數 ====================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 保留以備用
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# ==================== 從 Google Sheet 讀取訂閱者 ====================
def get_subscribers():
    """從 Google Sheet 讀取訂閱者名單（狀態為 active）"""
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("❌ 錯誤：GOOGLE_SERVICE_ACCOUNT_JSON 環境變數未設定")
        return []
    
    try:
        creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        records = sheet.get_all_records()
        
        subscribers = [row for row in records if row.get("狀態") == "active"]
        print(f"📋 從 Google Sheet 讀取到 {len(subscribers)} 位訂閱者")
        return subscribers
    except Exception as e:
        print(f"❌ 讀取 Google Sheet 失敗: {e}")
        return []

# ==================== 抓取當日最新文章 ====================
def get_today_article():
    """從 GitHub 讀取 daily-post 目錄中「今天」的最新文章"""
    try:
        url = "https://api.github.com/repos/fangyung0323/fb/contents/daily-post"
        headers = {"Accept": "application/vnd.github.v3+json"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        files = response.json()
        
        # 只取今天的日期
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 篩選出今天的文章
        today_files = [f for f in files if f["name"].startswith(today_str) and f["name"].endswith(".html") and f["name"] != "index.html"]
        
        if not today_files:
            print(f"❌ 沒有找到 {today_str} 的文章")
            return None, None, None, None
        
        # 按檔名排序，取最新的一篇
        today_files.sort(key=lambda x: x["name"], reverse=True)
        latest = today_files[0]
        
        article_url = f"https://www.fernbrom.com/daily-post/{latest['name']}"
        
        print(f"📰 找到今日文章: {latest['name']}")
        
        # 從文章 HTML 中讀取摘要和重點
        summary, key_points_html, title = get_article_summary(article_url)
        
        return title, summary, key_points_html, article_url
    except Exception as e:
        print(f"❌ 抓取文章失敗: {e}")
        return None, None, None, None

# ==================== 寄送 Email ====================
def send_email(to_email, to_name, title, summary, key_points_html, article_url):
    """寄送摘要信給單一訂閱者"""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("❌ 錯誤：寄信設定未完成")
        return False
    
    today = datetime.now().strftime("%Y/%m/%d")
    subject = f"🌿 蕨積每日摘要 - {today}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: 'Noto Sans TC', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #2c3e2f;">
        <h2 style="color: #3d5a38;">🌿 {to_name} 您好，</h2>
        <p>這是今天的蕨積每日摘要：</p>
        <hr style="border-color: #d4e4c8;">
        <div style="background: #faf8f4; padding: 16px; border-radius: 12px;">
            <p><strong>📌</strong> {summary}</p>
            <p><strong>✨ 重點整理：</strong></p>
            {key_points_html}
            <p><strong>👉 完整內容：</strong> <a href="{article_url}" style="color: #5a7a4a;">閱讀全文</a></p>
        </div>
        <hr style="border-color: #d4e4c8;">
        <p style="color: #9a9080; font-size: 12px; margin-top: 30px;">
            每天一篇，與你一起成長 🌿<br>
            <a href="https://www.fernbrom.com/subscribe.html" style="color: #9a9080;">取消訂閱</a>
        </p>
    </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ 寄送失敗 {to_email}: {e}")
        return False

# ==================== 主程式 ====================
def main():
    print("=" * 50)
    print("📧 蕨積每日摘要寄送機器人啟動")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 取得訂閱者名單
    subscribers = get_subscribers()
    if not subscribers:
        print("⚠️ 沒有訂閱者，結束程式")
        return
    
    # 2. 抓取當日文章摘要
    title, summary, key_points_html, article_url = get_today_article()
    if not title:
        print("❌ 無法取得文章，結束程式")
        return
    
    print(f"📝 今日文章：{title}")
    print(f"📋 摘要：{summary}")
    
    # 3. 寄送給所有訂閱者
    success_count = 0
    for sub in subscribers:
        name = sub.get("姓名", "讀者")
        email = sub.get("Email")
        if not email:
            continue
        
        if send_email(email, name, title, summary, key_points_html, article_url):
            success_count += 1
            print(f"✅ 已寄送給 {name} ({email})")
        else:
            print(f"❌ 寄送失敗 {name} ({email})")
    
    print(f"🎉 寄送完成：成功 {success_count} / 總共 {len(subscribers)} 位")
    print("=" * 50)

if __name__ == "__main__":
    main()
