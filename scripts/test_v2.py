"""Quick test: 1 team (Argentina) to verify shooting data from per-team page"""
import os, sys, json, time, shutil, tempfile
sys.path.insert(0, r'd:\AI\WorldCupGame\scripts')

from fetch_fbref_wcq_data_v2 import (
    copy_chrome_profile, create_driver, fetch_page,
    extract_table_from_soup, merge_player_data, team_url
)

DATA_DIR = r'd:\AI\WorldCupGame\data'
os.makedirs(DATA_DIR, exist_ok=True)

# Correct Argentina URL: https://fbref.com/en/squads/f9fddd6e/Argentina-Men-Stats
url = team_url("f9fddd6e", "Argentina")
print(f"目标URL: {url}")

print("复制 Chrome Profile...")
copy_chrome_profile()

print("启动 Chrome...")
driver = create_driver()
print("Chrome 启动成功!")

# 先访问 FBref 首页获取 Cloudflare cookie
print("\n访问 FBref 首页...")
driver.get("https://fbref.com")
import time as t2
for i in range(25):
    t2.sleep(3)
    src = driver.page_source
    if "正在进行安全验证" in src or "请稍候" in src:
        if i % 5 == 0:
            print(f"  等待 Cloudflare... ({(i+1)*3}s)")
    elif len(src) > 50000:
        print(f"  Cloudflare 已通过! ({(i+1)*3}s)")
        break
else:
    print("  超时，继续...")

print()

print(f"访问: {url}")
soup = fetch_page(url, driver)

if soup:
    print(f"页面获取成功! 长度: {len(str(soup))}")
    
    std = extract_table_from_soup(soup, "stats_standard")
    sh = extract_table_from_soup(soup, "stats_shooting")
    pt = extract_table_from_soup(soup, "stats_playing_time")
    misc = extract_table_from_soup(soup, "stats_misc")
    
    print(f"\nStandard:     {len(std or [])} rows")
    print(f"Shooting:     {len(sh or [])} rows")
    print(f"Playing Time: {len(pt or [])} rows")
    print(f"Misc:         {len(misc or [])} rows")
    
    if std:
        print(f"\nStandard 列名: {list(std[0].keys())}")
    if sh:
        print(f"Shooting 列名: {list(sh[0].keys())}")
    
    players = merge_player_data(std, sh, pt, misc)
    print(f"\n合并后: {len(players)} 名球员")
    
    top5 = sorted(players, key=lambda x: x.get("gls", 0), reverse=True)[:5]
    print(f"\n进球前5:")
    for p in top5:
        print(f"  {p['player']:22s} Gls:{p['gls']:2d} Sh:{p.get('sh',0):3d} SoT:{p.get('sot',0):3d} "
              f"SoT%:{p.get('sot_pct',0):5.1f} G/Sh:{p.get('g_sh',0):.2f} G/SoT:{p.get('g_sot',0):.2f} "
              f"MP:{p['mp']:2d} Min:{p['min']:4d} OG:{p.get('og',0)}")
    
    # Save test result
    out = os.path.join(DATA_DIR, "test_argentina_v2.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    print(f"\n已保存: {out}")
else:
    print("页面获取失败!")

driver.quit()
print("\n完成!")
