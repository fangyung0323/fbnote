#!/usr/bin/env python3
"""
每日摘要寄送機器人
- 從 Google Sheet 讀取訂閱者名單
- 從文章 HTML 中讀取預存的摘要（直接從 GitHub Raw 讀取，不受部署延遲影響）
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

# 導入共用工具函數
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import (
    check_today_article_exists, 
    check_today_email_sent, 
    mark_email_sent,
    get_today_main_article
)

# ==================== 讀取環境變數 ====================
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# ==================== 從 Google Sheet 讀取訂閱者 ====================
def get_subscribers():
    """從 Google Sheet 讀取訂閱者名單（狀態為 subscribed 或 active）"""
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
        
        # 支援 subscribed 或 active
        subscribers = [row for row in records if row.get("狀態") in ["active", "subscribed"]]
        print(f"📋 從 Google Sheet 讀取到 {len(subscribers)} 位訂閱者")
        return subscribers
    except Exception as e:
        print(f"❌ 讀取 Google Sheet 失敗: {e}")
        return []

# ==================== 從文章讀取摘要和重點 ====================
def get_article_summary(article_url):
    """從文章 HTML 中讀取預存的摘要和重點（自動轉換為 GitHub Raw）"""
    try:
        # 將網站網址轉換為 GitHub Raw 網址（避免等待 Render 部署）
        if "fernbrom.com" in article_url:
            filename = article_url.split('/')[-1]
            raw_url = f"https://raw.githubusercontent.com/isa930323-jpg/fb/main/daily-post/{filename}"
            print(f"📡 從 GitHub Raw 讀取: {raw_url}")
            response = requests.get(raw_url)
        else:
            response = requests.get(article_url)
        
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 讀取標題
        title_tag = soup.find('h1', class_='article-title')
        title = title_tag.text if title_tag else "無標題"
        
        # 從 meta 標籤讀取摘要
        summary_meta = soup.find('meta', {'name': 'article-summary'})
        summary = summary_meta['content'] if summary_meta else "無法讀取摘要"
        
        # 從 meta 標籤讀取重點
        keypoints_meta = soup.find('meta', {'name': 'article-keypoints'})
        if keypoints_meta:
            try:
                key_points = json.loads(keypoints_meta['content'])
                key_points_html = "<ul>" + "".join([f"<li>{point}</li>" for point in key_points]) + "</ul>"
            except:
                key_points_html = "<ul><li>無法讀取重點</li></ul>"
        else:
            key_points_html = "<ul><li>無法讀取重點</li></ul>"
        
        return summary, key_points_html, title
    except Exception as e:
        print(f"❌ 讀取文章摘要失敗: {e}")
        return "無法讀取摘要", "<ul><li>無法讀取重點</li></ul>", "無標題"

# ==================== 抓取當日文章（使用統一邏輯） ====================
def get_today_article():
    """從 GitHub API 讀取今日文章（使用統一的選擇邏輯）"""
    article_filename = get_today_main_article()
    
    if not article_filename:
        print("❌ 找不到今日文章")
        return None, None, None, None
    
    # 建構文章 URL
    article_url = f"https://www.fernbrom.com/daily-post/{article_filename}"
    
    print(f"📰 找到今日文章: {article_filename}")
    
    # 從文章 HTML 中讀取摘要和重點
    summary, key_points_html, title = get_article_summary(article_url)
    
    return title, summary, key_points_html, article_url

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
        <h2 style="color: #3d5a38;">🌿親愛的{to_name}您好，</h2>
        <p>蕨積|每日摘要：</p>
        <hr style="border-color: #d4e4c8;">
        <div style="background: #faf8f4; padding: 16px; border-radius: 12px;">
            <p><strong>📖 文章名稱：</strong> {title}</p>
            <p><strong>📌 摘要：</strong> {summary}</p>
            <p><strong>✨ 重點整理：</strong></p>
            {key_points_html}
             <p><strong>👉</strong> <a href="article_url" style="color: #5a7a4a;">今日完整文章</a></p>
            <p><strong>👉</strong> <a href="https://www.fernbrom.com/daily-post/" style="color: #5a7a4a;">閱讀更多</a></p>
        </div>
        <hr style="border-color: #d4e4c8;">
        <p style="color: #9a9080; font-size: 12px; margin-top: 30px;">
            每天一篇，與你一起成長 🌿<br>
            <a href="https://www.fernbrom.com/sub.html" style="color: #9a9080;">取消訂閱</a>
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
    
    # ========== 除錯：直接檢查 GitHub API ==========
    print("\n🔍 開始除錯檢查...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"今天的日期: {today_str}")
    
    url = "https://api.github.com/repos/isa930323-jpg/fb/contents/daily-post"
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print("✅ GH_TOKEN 已設定")
    else:
        print("❌ GH_TOKEN 未設定")
    
    response = requests.get(url, headers=headers)
    print(f"GitHub API 回應狀態: {response.status_code}")
    
    if response.status_code == 200:
        files = response.json()
        today_files = []
        for file in files:
            if file["name"].startswith(today_str) and file["name"].endswith(".html"):
                today_files.append(file["name"])
        
        print(f"找到的今日文章: {today_files}")
        if today_files:
            print(f"✅ 應該要找到文章！")
        else:
            print(f"❌ 沒有找到今日文章")
            print(f"最近的文章: {[f['name'] for f in files[:5]]}")
    else:
        print(f"❌ API 呼叫失敗: {response.text[:200]}")
    
    print("=" * 50)
    # ========== 除錯結束 ==========
    
    # 暫時註解防重複檢查
    # if not check_today_article_exists():
    #     print("❌ 今天還沒有新文章，跳過寄信")
    #     print("💡 請先執行發文機器人")
    #     return
    
    if check_today_email_sent():
        print("❌ 今天已經寄過摘要信了，跳過本次寄送")
        print("💡 如需重新寄送，請手動刪除對應的 Git Tag")
        return
    
    # 1. 取得訂閱者名單
    subscribers = get_subscribers()
    if not subscribers:
        print("⚠️ 沒有訂閱者，結束程式")
        return
    
    # 2. 抓取當日文章（使用統一邏輯）
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
    
    if success_count > 0:
        mark_email_sent()
    
    print("=" * 50)

if __name__ == "__main__":
    main()
