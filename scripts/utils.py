#!/usr/bin/env python3
"""
共用工具函數 - 防重複機制
"""

import os
import requests
from datetime import datetime

# GitHub 倉庫設定
GITHUB_REPO_OWNER = "fangyung0323"  # 改成你的使用者名稱
GITHUB_REPO_NAME = "fb"  # 倉庫名稱
DAILY_POST_PATH = "daily-post"

def get_today_str():
    """取得今天的日期字串 YYYY-MM-DD"""
    return datetime.now().strftime("%Y-%m-%d")

def check_today_article_exists():
    """
    檢查今天是否已經有文章
    回傳 True: 已有文章, False: 尚無文章
    """
    today_str = get_today_str()
    
    # 方法1：從本地 articles 目錄檢查（如果存在）
    if os.path.exists("articles"):
        try:
            for f in os.listdir("articles"):
                if f.startswith(today_str) and f.endswith(".html"):
                    print(f"⚠️ 本地已存在今日文章：{f}")
                    return True
        except Exception as e:
            print(f"⚠️ 檢查本地目錄時發生錯誤：{e}")
    
    # 方法2：從 GitHub API 檢查遠端倉庫
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{DAILY_POST_PATH}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        # 如果有 GitHub Token，加入 header 提高限流上限
        token = os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            files = response.json()
            today_files = []
            
            for file in files:
                if file["name"].startswith(today_str) and file["name"].endswith(".html"):
                    today_files.append(file["name"])
            
            if today_files:
                print(f"⚠️ 遠端已存在今日文章：{', '.join(today_files)}")
                return True
        elif response.status_code == 404:
            # 目錄不存在，表示還沒有任何文章
            return False
        else:
            print(f"⚠️ GitHub API 回應錯誤：{response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 無法連線到 GitHub API：{e}")
    except Exception as e:
        print(f"⚠️ 檢查遠端文章時發生錯誤：{e}")
    
    return False

def check_today_email_sent():
    """
    檢查今天是否已經寄過信
    使用 GitHub 的 Tag 或 Release 來記錄
    回傳 True: 已寄過, False: 尚未寄送
    """
    today_str = get_today_str()
    tag_name = f"email-sent-{today_str}"
    
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/git/ref/tags/{tag_name}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        token = os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            print(f"⚠️ 今天 ({today_str}) 已經寄過信了")
            return True
        elif response.status_code == 404:
            return False
        else:
            print(f"⚠️ 檢查寄信記錄時發生錯誤：{response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️ 檢查寄信記錄時發生錯誤：{e}")
        return False

def mark_email_sent():
    """
    標記今天已經寄過信（建立一個 Git Tag）
    """
    today_str = get_today_str()
    tag_name = f"email-sent-{today_str}"
    
    try:
        # 建立一個輕量級 tag
        cmd = f'git tag {tag_name}'
        result = os.system(cmd)
        
        if result == 0:
            # 推送到遠端
            push_cmd = f'git push origin {tag_name}'
            os.system(push_cmd)
            print(f"✅ 已標記今日 ({today_str}) 信件已寄送")
            return True
        else:
            print(f"⚠️ 無法建立 tag：{tag_name}")
            return False
            
    except Exception as e:
        print(f"⚠️ 標記寄信記錄時發生錯誤：{e}")
        return False

def get_today_main_article():
    """
    取得今天的主打文章（統一邏輯）
    回傳: 文章檔名，或 None
    """
    today_str = get_today_str()
    
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{DAILY_POST_PATH}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        token = os.getenv("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            files = response.json()
            today_files = []
            
            for file in files:
                if file["name"].startswith(today_str) and file["name"].endswith(".html"):
                    today_files.append(file["name"])
            
            if not today_files:
                print(f"❌ 找不到今天的文章：{today_str}")
                return None
            
            # 按檔名排序，取第一篇（確保與 index 一致）
            today_files.sort(key=lambda x: x)  # 字母順序正序
            selected = today_files[0]
            print(f"📌 選擇今日主打文章：{selected}")
            return selected
            
    except Exception as e:
        print(f"❌ 取得今日文章時發生錯誤：{e}")
        return None
