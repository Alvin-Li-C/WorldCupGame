"""
FBref WCQ 数据爬取 - 使用用户 Chrome Profile 绕过 Cloudflare
方案: 复制用户 Chrome Profile 的 cookies 用于 Selenium
"""
import os
import sys
import json
import time
import shutil
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from bs4 import Comment
import pandas as pd

# 10支热门球队
TEAMS = {
    "西班牙": {"id": "b561dd30", "confed": "UEFA", "en_name": "Spain"},
    "阿根廷": {"id": "a22c25fc", "confed": "CONMEBOL", "en_name": "Argentina"},
    "法国": {"id": "d326e8e3", "confed": "UEFA", "en_name": "France"},
    "英格兰": {"id": "195a7302", "confed": "UEFA", "en_name": "England"},
    "巴西": {"id": "2cdc1f7c", "confed": "CONMEBOL", "en_name": "Brazil"},
    "德国": {"id": "978e5e4d", "confed": "UEFA", "en_name": "Germany"},
    "葡萄牙": {"id": "837e3b29", "confed": "UEFA", "en_name": "Portugal"},
    "荷兰": {"id": "6a8de82e", "confed": "UEFA", "en_name": "Netherlands"},
    "比利时": {"id": "da39b04f", "confed": "UEFA", "en_name": "Belgium"},
    "哥伦比亚": {"id": "11b1e72c", "confed": "CONMEBOL", "en_name": "Colombia"},
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

WCQ_URLS = {
    "UEFA": "https://fbref.com/en/comps/6/stats/WCQ----UEFA-M-Stats",
    "CONMEBOL": "https://fbref.com/en/comps/4/stats/WCQ----CONMEBOL-M-Stats",
}

# 用户 Chrome Profile 路径
CHROME_PROFILE_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
TEMP_PROFILE_PATH = os.path.join(tempfile.gettempdir(), "chrome_selenium_profile")


def copy_chrome_profile():
    """复制用户 Chrome Profile 中的 cookies 和 Cloudflare 数据"""
    if not os.path.exists(CHROME_PROFILE_PATH):
        print(f"  Chrome Profile 不存在: {CHROME_PROFILE_PATH}")
        return False
    
    # 只复制关键文件（cookies, local storage 等）
    default_dir = os.path.join(CHROME_PROFILE_PATH, "Default")
    if not os.path.exists(default_dir):
        print(f"  Default profile 不存在: {default_dir}")
        return False
    
    dest_default = os.path.join(TEMP_PROFILE_PATH, "Default")
    os.makedirs(dest_default, exist_ok=True)
    
    # 复制 Local State
    local_state = os.path.join(CHROME_PROFILE_PATH, "Local State")
    if os.path.exists(local_state):
        shutil.copy2(local_state, os.path.join(TEMP_PROFILE_PATH, "Local State"))
    
    # 复制 cookies 和 storage 相关文件
    files_to_copy = ["Cookies", "Cookies-journal", "Login Data", "Login Data-journal",
                     "Web Data", "Web Data-journal", "Preferences", "Secure Preferences"]
    
    for f in files_to_copy:
        src = os.path.join(default_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest_default, f))
    
    # 复制 Local Storage
    ls_src = os.path.join(default_dir, "Local Storage")
    ls_dst = os.path.join(dest_default, "Local Storage")
    if os.path.exists(ls_src):
        if os.path.exists(ls_dst):
            shutil.rmtree(ls_dst)
        shutil.copytree(ls_src, ls_dst)
    
    # 复制 IndexedDB (可能包含 Cloudflare tokens)
    idb_src = os.path.join(default_dir, "IndexedDB")
    idb_dst = os.path.join(dest_default, "IndexedDB")
    if os.path.exists(idb_src):
        if os.path.exists(idb_dst):
            shutil.rmtree(idb_dst)
        shutil.copytree(idb_src, idb_dst, ignore_dangling_symlinks=True)
    
    print(f"  Chrome Profile cookies 已复制到: {TEMP_PROFILE_PATH}")
    return True


def create_driver(use_profile=False):
    """创建 Selenium Chrome WebDriver"""
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    if use_profile and os.path.exists(TEMP_PROFILE_PATH):
        options.add_argument(f"--user-data-dir={TEMP_PROFILE_PATH}")
        print("  使用复制的 Chrome Profile")
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_fbref_page(url, driver, retries=3):
    """获取 FBref 页面"""
    for attempt in range(retries):
        try:
            print(f"  请求: {url} (尝试 {attempt+1}/{retries})")
            driver.get(url)
            
            max_wait = 45
            waited = 0
            while waited < max_wait:
                time.sleep(3)
                waited += 3
                page_source = driver.page_source
                
                if "正在进行安全验证" in page_source or "Just a moment" in page_source or "请稍候" in page_source:
                    print(f"  等待 Cloudflare 验证... ({waited}s)")
                    continue
                
                if "stats_standard" in page_source or "Standard Stats" in page_source:
                    print(f"  页面获取成功! (长度: {len(page_source)}, 等待: {waited}s)")
                    return BeautifulSoup(page_source, "html.parser")
                
                if len(page_source) > 200000:
                    print(f"  大页面已加载 (长度: {len(page_source)}, 等待: {waited}s)")
                    return BeautifulSoup(page_source, "html.parser")
            
            # 超时前保存当前页面用于调试
            page_source = driver.page_source
            print(f"  等待超时 ({max_wait}s), 页面长度: {len(page_source)}")
            print(f"  页面标题: {driver.title}")
            
            if len(page_source) > 50000:
                return BeautifulSoup(page_source, "html.parser")
                
        except Exception as e:
            print(f"  请求异常: {e}")
            time.sleep(5)
    
    return None


def parse_fbref_stats_table(soup, table_id="stats_standard"):
    """解析 FBref 统计数据表格"""
    # 先尝试直接查找
    table = soup.find("table", {"id": table_id})
    
    # 如果没找到，尝试在 HTML 注释中查找
    if not table:
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        for comment in comments:
            if table_id in comment:
                comment_soup = BeautifulSoup(comment, "html.parser")
                table = comment_soup.find("table", {"id": table_id})
                if table:
                    print(f"  从HTML注释中提取了 #{table_id}")
                    break
    
    if not table:
        # 尝试查找任何包含 player 数据的表格
        all_tables = soup.find_all("table")
        print(f"  未找到 #{table_id}，页面共 {len(all_tables)} 个表格:")
        for t in all_tables[:10]:
            tid = t.get("id", "(无ID)")
            rows = len(t.find_all("tr"))
            print(f"    - #{tid} ({rows} 行)")
        return None

    # 获取表头
    headers = []
    thead = table.find("thead")
    if thead:
        for th in thead.find_all("th"):
            stat = th.get("data-stat", "")
            if stat:
                headers.append(stat)

    # 获取数据行
    rows = []
    tbody = table.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            if tr.get("class") and "thead" in tr.get("class", []):
                continue
            row = {}
            for th in tr.find_all("th"):
                stat = th.get("data-stat", "")
                if stat:
                    row[stat] = th.get_text(strip=True)
            for td in tr.find_all("td"):
                stat = td.get("data-stat", "")
                if stat:
                    row[stat] = td.get_text(strip=True)
            if row:
                rows.append(row)

    if rows:
        return pd.DataFrame(rows)
    return None


def filter_team_players(df, team_en_name):
    """从大洲数据中筛选特定球队球员"""
    if df is None:
        return []
    
    players = []
    for _, row in df.iterrows():
        team = str(row.get("team", row.get("nationality", "")))
        if team_en_name.lower() not in team.lower():
            continue
        
        player_data = {
            "player": str(row.get("player", "")),
            "pos": str(row.get("position", "")),
            "age": _safe_int(row.get("age", 0)),
            "gls": _safe_int(row.get("goals", 0)),
            "ast": _safe_int(row.get("assists", 0)),
            "ga": _safe_int(row.get("goals_assists", 0)),
            "g_pk": _safe_int(row.get("goals_pens", 0)),
            "pk": _safe_int(row.get("pens_made", 0)),
            "pkatt": _safe_int(row.get("pens_att", 0)),
            "nineties": _safe_float(row.get("minutes_90s", 0)),
            "mp": _safe_int(row.get("games", 0)),
            "starts": _safe_int(row.get("games_starts", 0)),
            "min": _safe_int(row.get("minutes", 0)),
            "cry": _safe_int(row.get("cards_yellow", 0)),
            "crr": _safe_int(row.get("cards_red", 0)),
            "og": _safe_int(row.get("own_goals", 0)),
            # per-90 数据
            "gls_per90": _safe_float(row.get("goals_per90", 0)),
            "ast_per90": _safe_float(row.get("assists_per90", 0)),
            "ga_per90": _safe_float(row.get("goals_assists_per90", 0)),
            "gpk_per90": _safe_float(row.get("goals_pens_per90", 0)),
        }
        players.append(player_data)
    
    return players


def _safe_int(val):
    try:
        if pd.isna(val):
            return 0
        return int(float(str(val)))
    except (ValueError, TypeError):
        return 0


def _safe_float(val):
    try:
        if pd.isna(val):
            return 0.0
        return round(float(str(val)), 2)
    except (ValueError, TypeError):
        return 0.0


def main():
    print("=" * 60)
    print("FBref 世界杯预选赛(WCQ)数据爬取")
    print("=" * 60)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, "wcq_player_stats.json")
    
    # 复制 Chrome Profile
    print("\n步骤1: 复制 Chrome Profile cookies...")
    print("  (请确保 Chrome 已关闭，否则 cookies 可能被锁定)")
    use_profile = copy_chrome_profile()
    
    # 按大洲分组
    confeds = {}
    for team_cn, info in TEAMS.items():
        confed = info["confed"]
        if confed not in confeds:
            confeds[confed] = []
        confeds[confed].append(team_cn)
    
    all_data = {}
    
    # 创建 WebDriver
    print(f"\n步骤2: 启动 Chrome 浏览器...")
    try:
        driver = create_driver(use_profile=use_profile)
        print("Chrome 启动成功！")
    except Exception as e:
        print(f"Chrome 启动失败: {e}")
        return
    
    try:
        for confed, team_names in confeds.items():
            print(f"\n{'='*40}")
            print(f"大洲: {confed} — 球队: {', '.join(team_names)}")
            print(f"{'='*40}")
            
            url = WCQ_URLS.get(confed)
            if not url:
                continue
            
            soup = fetch_fbref_page(url, driver)
            
            if soup:
                # 保存调试HTML
                debug_path = os.path.join(DATA_DIR, f"debug_{confed}.html")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))
                
                df = parse_fbref_stats_table(soup, "stats_standard")
                
                if df is not None and len(df) > 0:
                    print(f"  成功获取 {len(df)} 名球员数据")
                    print(f"  表格列: {list(df.columns)[:10]}...")
                else:
                    print(f"  未能解析 {confed} 数据表格")
                    df = None
            else:
                print(f"  未能获取 {confed} 页面")
                df = None
            
            for team_cn in team_names:
                team_info = TEAMS[team_cn]
                print(f"\n  筛选 {team_cn} ({team_info['en_name']}) ...")
                players = filter_team_players(df, team_info["en_name"])
                all_data[team_cn] = players
                print(f"  {team_cn}: {len(players)} 名球员")
                
                for p in players[:3]:
                    print(f"    {p.get('player','?')} | {p.get('pos','?')} | "
                          f"Gls:{p.get('gls',0)} | Sh:{p.get('sh',0)} | "
                          f"MP:{p.get('mp',0)} | Min:{p.get('min',0)}")
            
            time.sleep(5)
    
    finally:
        driver.quit()
        print("\nChrome 浏览器已关闭")
        # 清理临时 profile
        if os.path.exists(TEMP_PROFILE_PATH):
            try:
                shutil.rmtree(TEMP_PROFILE_PATH)
            except:
                pass
    
    # 保存JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"爬取完成！输出文件: {output_path}")
    print(f"{'='*60}")
    total = 0
    for team_cn, players in all_data.items():
        count = len(players)
        total += count
        status = "OK" if count > 0 else "EMPTY"
        print(f"  {team_cn}: {count} 名球员 [{status}]")
    print(f"\n总计: {total} 名球员 / {len(all_data)} 支球队")


if __name__ == "__main__":
    main()
