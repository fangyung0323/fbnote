def main():
    print("=" * 50)
    print("🌿 蕨積每日發文機器人啟動")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"環境變數檢查:")
    print(f"  DEEPSEEK_API_KEY: {'已設定' if DEEPSEEK_API_KEY else '❌ 未設定'}")
    print(f"  GH_TOKEN: {'已設定' if os.getenv('GH_TOKEN') else '❌ 未設定'}")
    print(f"  GITHUB_USERNAME: {os.getenv('GITHUB_USERNAME')}")
    print(f"  WEBSITE_REPO_NAME: {os.getenv('WEBSITE_REPO_NAME')}")
    print("=" * 50)
    
    # 1. 生成文章
    print("\n📝 步驟 1: 生成文章...")
    title, content = generate_article()
    if not title or not content:
        print("❌ 文章生成失敗，結束程式")
        sys.exit(1)
    print(f"✅ 文章生成成功: {title}")
    
    # 2. 儲存文章
    print("\n💾 步驟 2: 儲存文章...")
    save_article_as_html(title, content)
    print("✅ 文章儲存完成")
    
    # 3. 推送到網站倉庫
    print("\n🚀 步驟 3: 推送到網站倉庫...")
    commit_and_push_to_website()
    
    print("\n🎉 每日發文流程完成")
