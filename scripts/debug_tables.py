"""Debug: check what tables exist in the Argentina page HTML"""
import os, sys, time, shutil, tempfile
sys.path.insert(0, r'd:\AI\WorldCupGame\scripts')

from fetch_fbref_wcq_data_v2 import (
    copy_chrome_profile, create_driver, fetch_page, team_url
)
from bs4 import BeautifulSoup, Comment

DATA_DIR = r'd:\AI\WorldCupGame\data'
os.makedirs(DATA_DIR, exist_ok=True)

url = team_url("f9fddd6e", "Argentina")
print(f"目标URL: {url}")

print("复制 Chrome Profile...")
copy_chrome_profile()

print("启动 Chrome...")
driver = create_driver()
print("Chrome 启动成功!")

print("\n访问 FBref 首页...")
driver.get("https://fbref.com")
for i in range(25):
    time.sleep(3)
    src = driver.page_source
    if "正在进行安全验证" in src or "请稍候" in src:
        if i % 5 == 0:
            print(f"  等待 Cloudflare... ({(i+1)*3}s)")
    elif len(src) > 50000:
        print(f"  Cloudflare 已通过! ({(i+1)*3}s)")
        break

print(f"\n访问: {url}")
soup = fetch_page(url, driver)

if soup:
    print(f"页面长度: {len(str(soup))}")
    
    # 1. Find all table IDs in direct HTML
    tables = soup.find_all("table")
    print(f"\n直接HTML中的表格 ({len(tables)}):")
    for t in tables:
        tid = t.get("id", "NO_ID")
        rows = len(t.find_all("tr")) if t.find("tbody") else 0
        print(f"  id={tid:40s} rows={rows}")
    
    # 2. Find all tables in HTML comments
    comments = soup.find_all(string=lambda t: isinstance(t, Comment))
    print(f"\nHTML注释数量: {len(comments)}")
    comment_tables = 0
    for c in comments:
        cs = BeautifulSoup(c, "html.parser")
        for t in cs.find_all("table"):
            tid = t.get("id", "NO_ID")
            rows = len(t.find_all("tr")) if t.find("tbody") else 0
            print(f"  [注释] id={tid:40s} rows={rows}")
            comment_tables += 1
    print(f"注释中的表格总数: {comment_tables}")
    
    # 3. Look for specific keywords
    html_str = str(soup)
    for keyword in ["stats_standard", "stats_shooting", "stats_playing_time", "stats_misc",
                     "Standard Stats", "Shooting", "Playing Time"]:
        count = html_str.count(keyword)
        print(f"  '{keyword}' 出现次数: {count}")
    
    # 4. Save raw HTML for inspection
    raw_path = os.path.join(DATA_DIR, "debug_argentina.html")
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(str(soup))
    print(f"\n已保存原始HTML: {raw_path}")
else:
    print("页面获取失败!")

driver.quit()
print("\n完成!")
