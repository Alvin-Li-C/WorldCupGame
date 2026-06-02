"""
FBref WCQ 数据爬取 V2 - 按球队页面爬取

Phase 1: 从世界杯资格赛页面自动发现所有48支球队链接
Phase 2: 逐个访问每支球队页面，提取:
  - Standard Stats: 基本数据(进球, 助攻, 出场等)
  - Shooting: 射门数据(Sh, SoT, G/Sh, G/SoT)
  - Playing Time: 出场时间(MP, Starts, Min, 90s)
  - Miscellaneous: 杂项(OG 乌龙球, 黄红牌)

数据源: FBref 各球队独立页面
"""
import os
import sys
import json
import time
import shutil
import tempfile
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, Comment
import pandas as pd

# 输出目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Chrome Profile 路径
CHROME_PROFILE_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
TEMP_PROFILE_PATH = os.path.join(tempfile.gettempdir(), "chrome_selenium_profile")

# 世界杯资格赛总页面 (用于发现所有48支球队链接)
WCQ_OVERVIEW_URL = "https://fbref.com/en/comps/1/qual/World-Cup-Qualifying-Rounds"

# 已知球队 squad ID 映射 (从搜索结果中收集)
# 脚本会先从WCQ页面自动发现，这里作为备用
KNOWN_TEAMS = {
    "Argentina": "f9fddd6e",
    "Brazil": "304635c3",
    "France": "b1b36dcd",
    "Spain": "b561dd30",
    "Germany": "c1e40422",
    "England": "1862c019",
    "Portugal": "4a1b4ea8",
    "Netherlands": "5bb5024a",
    "Belgium": "361422b9",
    "Italy": "998c5958",
    "Croatia": "7b08e376",
    "Denmark": "29a4e4af",
    "Switzerland": "81021a70",
    "Norway": "599eba19",
    "Scotland": "602d3994",
    "Uruguay": "870e020f",
    "Colombia": "ab73cfe5",
    "Ecuador": "123acaf8",
    "Paraguay": "d2043442",
    "United States": "0f66725b",
    "Mexico": "b009a548",
    "Japan": "ffcf1690",
    "Korea Republic": "473f0fbf",
}

# 球队页面 URL 格式: https://fbref.com/en/squads/{id}/{Team}-Men-Stats
def team_url(squad_id, team_slug):
    return f"https://fbref.com/en/squads/{squad_id}/{team_slug}-Men-Stats"

# 需要爬取的表格 (section hash -> 表格ID前缀)
STAT_SECTIONS = {
    "stats_standard": "Standard Stats",
    "stats_shooting": "Shooting",
    "stats_playing_time": "Playing Time",
    "stats_misc": "Miscellaneous Stats",
}


def copy_chrome_profile():
    """复制用户 Chrome Profile cookies"""
    if not os.path.exists(CHROME_PROFILE_PATH):
        return False
    default_dir = os.path.join(CHROME_PROFILE_PATH, "Default")
    if not os.path.exists(default_dir):
        return False
    
    # 清理旧的临时 profile
    if os.path.exists(TEMP_PROFILE_PATH):
        try:
            shutil.rmtree(TEMP_PROFILE_PATH)
        except PermissionError:
            # 文件被锁定，尝试重命名
            try:
                old_path = TEMP_PROFILE_PATH + "_old"
                if os.path.exists(old_path):
                    shutil.rmtree(old_path, ignore_errors=True)
                os.rename(TEMP_PROFILE_PATH, old_path)
            except:
                pass
    
    dest_default = os.path.join(TEMP_PROFILE_PATH, "Default")
    os.makedirs(dest_default, exist_ok=True)
    
    local_state = os.path.join(CHROME_PROFILE_PATH, "Local State")
    if os.path.exists(local_state):
        shutil.copy2(local_state, os.path.join(TEMP_PROFILE_PATH, "Local State"))
    
    for f in ["Cookies", "Cookies-journal", "Preferences", "Secure Preferences"]:
        src = os.path.join(default_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest_default, f))
    
    for d in ["Local Storage", "IndexedDB"]:
        src = os.path.join(default_dir, d)
        dst = os.path.join(dest_default, d)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst, ignore_errors=True)
            try:
                shutil.copytree(src, dst, ignore_dangling_symlinks=True)
            except Exception:
                pass  # 如果复制失败就跳过
    
    return True


def create_driver():
    """创建 Selenium Chrome WebDriver"""
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    if os.path.exists(TEMP_PROFILE_PATH):
        options.add_argument(f"--user-data-dir={TEMP_PROFILE_PATH}")
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_page(url, driver, retries=3):
    """获取页面，处理 Cloudflare 验证"""
    for attempt in range(retries):
        try:
            driver.get(url)
            max_wait = 60
            waited = 0
            while waited < max_wait:
                time.sleep(3)
                waited += 3
                src = driver.page_source
                
                if "正在进行安全验证" in src or "请稍候" in src or "Just a moment" in src:
                    if waited % 15 == 0:
                        print(f"    等待 Cloudflare... ({waited}s)")
                    continue
                
                if len(src) > 100000:
                    return BeautifulSoup(src, "html.parser")
                
                # 小页面可能是真实的（某些小球队数据少）
                if waited >= 15 and len(src) > 30000:
                    return BeautifulSoup(src, "html.parser")
            
            src = driver.page_source
            print(f"    尝试 {attempt+1}/{retries} 超时, 页面长度: {len(src)}, 标题: {driver.title}")
            if len(src) > 200000:
                return BeautifulSoup(src, "html.parser")
            # 继续重试
            
        except Exception as e:
            print(f"    异常: {e}")
            time.sleep(5)
    
    return None


def extract_table_from_soup(soup, table_id_prefix):
    """从 soup 中提取表格（包括 HTML 注释中的表格）
    使用 starts_with 匹配，因为 FBref 表格 ID 可能有后缀如 stats_standard_4
    """
    # 直接查找 (ID 以 prefix 开头)
    table = soup.find("table", id=lambda x: x and x.startswith(table_id_prefix))
    
    # 在 HTML 注释中查找
    if not table:
        comments = soup.find_all(string=lambda t: isinstance(t, Comment))
        for comment in comments:
            if table_id_prefix in comment:
                cs = BeautifulSoup(comment, "html.parser")
                table = cs.find("table", id=lambda x: x and x.startswith(table_id_prefix))
                if table:
                    break
    
    if not table:
        return None
    
    # 解析表头
    headers = []
    thead = table.find("thead")
    if thead:
        for th in thead.find_all("th"):
            stat = th.get("data-stat", "")
            if stat and stat not in headers:
                headers.append(stat)
    
    # 解析数据行
    rows = []
    tbody = table.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            if tr.get("class") and "thead" in tr.get("class", []):
                continue
            row = {}
            for elem in tr.find_all(["th", "td"]):
                stat = elem.get("data-stat", "")
                if stat:
                    row[stat] = elem.get_text(strip=True)
            if row:
                rows.append(row)
    
    return rows


def merge_player_data(standard_rows, shooting_rows, playing_time_rows, misc_rows):
    """合并多个表格的球员数据，以 player 为 key"""
    players = {}
    
    def get_key(row):
        return row.get("player", "").strip()
    
    # Standard Stats 是基础
    for row in (standard_rows or []):
        key = get_key(row)
        if not key:
            continue
        players[key] = {
            "player": key,
            "pos": row.get("position", ""),
            "age": _safe_int(row.get("age", 0)),
            "mp": _safe_int(row.get("games", 0)),
            "starts": _safe_int(row.get("games_starts", 0)),
            "min": _safe_int(row.get("minutes", 0)),
            "nineties": _safe_float(row.get("minutes_90s", 0)),
            "gls": _safe_int(row.get("goals", 0)),
            "ast": _safe_int(row.get("assists", 0)),
            "ga": _safe_int(row.get("goals_assists", 0)),
            "g_pk": _safe_int(row.get("goals_pens", 0)),
            "pk": _safe_int(row.get("pens_made", 0)),
            "pkatt": _safe_int(row.get("pens_att", 0)),
            "cry": _safe_int(row.get("cards_yellow", 0)),
            "crr": _safe_int(row.get("cards_red", 0)),
            "gls_per90": _safe_float(row.get("goals_per90", 0)),
            "ast_per90": _safe_float(row.get("assists_per90", 0)),
        }
    
    # Shooting 补充射门数据
    for row in (shooting_rows or []):
        key = get_key(row)
        if key in players:
            players[key]["sh"] = _safe_int(row.get("shots", 0))
            players[key]["sot"] = _safe_int(row.get("shots_on_target", 0))
            players[key]["sot_pct"] = _safe_float(row.get("shots_on_target_pct", 0))
            players[key]["sh_per90"] = _safe_float(row.get("shots_per90", 0))
            players[key]["sot_per90"] = _safe_float(row.get("shots_on_target_per90", 0))
            players[key]["g_sh"] = _safe_float(row.get("goals_per_shot", 0))
            players[key]["g_sot"] = _safe_float(row.get("goals_per_shot_on_target", 0))
            # PK from shooting if not in standard
            if players[key]["pk"] == 0:
                players[key]["pk"] = _safe_int(row.get("pens_made", 0))
            if players[key]["pkatt"] == 0:
                players[key]["pkatt"] = _safe_int(row.get("pens_att", 0))
    
    # Playing Time 补充出场数据
    for row in (playing_time_rows or []):
        key = get_key(row)
        if key in players:
            if players[key]["mp"] == 0:
                players[key]["mp"] = _safe_int(row.get("games", 0))
            if players[key]["starts"] == 0:
                players[key]["starts"] = _safe_int(row.get("games_starts", 0))
            if players[key]["min"] == 0:
                players[key]["min"] = _safe_int(row.get("minutes", 0))
    
    # Misc 补充乌龙球
    for row in (misc_rows or []):
        key = get_key(row)
        if key in players:
            players[key]["og"] = _safe_int(row.get("own_goals", 0))
            # 补充黄红牌如果标准表没有
            if players[key]["cry"] == 0:
                players[key]["cry"] = _safe_int(row.get("cards_yellow", 0))
            if players[key]["crr"] == 0:
                players[key]["crr"] = _safe_int(row.get("cards_red", 0))
    
    return list(players.values())


def _safe_int(val):
    try:
        if val is None or val == "" or (isinstance(val, float) and pd.isna(val)):
            return 0
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return 0


def _safe_float(val):
    try:
        if val is None or val == "" or (isinstance(val, float) and pd.isna(val)):
            return 0.0
        return round(float(str(val).replace(",", "").replace("%", "")), 2)
    except (ValueError, TypeError):
        return 0.0


def discover_teams(driver):
    """从WCQ总页面发现所有48支球队链接"""
    print("\n步骤4: 从WCQ页面发现所有球队链接...")
    print(f"  访问: {WCQ_OVERVIEW_URL}")
    
    soup = fetch_page(WCQ_OVERVIEW_URL, driver)
    if not soup:
        print("  ❌ 无法获取WCQ总页面，使用已知球队列表...")
        return None
    
    # 查找所有 /en/squads/{id}/{name}-Men-Stats 格式的链接
    teams = {}
    pattern = re.compile(r'/en/squads/([a-f0-9]+)/([\w-]+)-Men-Stats')
    
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").split("#")[0]  # 去掉 anchor
        m = pattern.search(href)
        if m:
            squad_id = m.group(1)
            slug = m.group(2)
            # 跳过重复 (同一个队可能出现在多处)
            if slug not in teams:
                teams[slug] = squad_id
    
    if not teams:
        print("  ⚠ 未发现球队链接，使用已知列表")
        return None
    
    print(f"  ✓ 发现 {len(teams)} 支球队:")
    for slug, sid in sorted(teams.items()):
        print(f"    {slug:25s} -> {sid}")
    
    return teams


def main():
    print("=" * 60)
    print("FBref WCQ 数据爬取 V2 — 按球队页面")
    print("=" * 60)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    output_path = os.path.join(DATA_DIR, "wcq_player_stats.json")
    
    # 复制 Chrome Profile
    print("\n步骤1: 复制 Chrome Profile...")
    copy_chrome_profile()
    
    # 创建 WebDriver
    print("步骤2: 启动 Chrome...")
    driver = create_driver()
    print("Chrome 启动成功！")
    
    # 先访问 FBref 首页通过 Cloudflare 验证
    print("\n步骤3: 访问 FBref 首页获取 Cloudflare 验证...")
    driver.get("https://fbref.com")
    for i in range(25):  # 最多等 75 秒
        time.sleep(3)
        src = driver.page_source
        if "正在进行安全验证" in src or "请稍候" in src:
            if i % 5 == 0:
                print(f"  等待 Cloudflare... ({(i+1)*3}s)")
        elif len(src) > 50000:
            print(f"  Cloudflare 已通过! (等待: {(i+1)*3}s)")
            break
    else:
        print("  Cloudflare 验证超时，继续尝试...")
    
    # Phase 1: 发现球队
    discovered_teams = discover_teams(driver)
    
    # 如果没有发现，使用已知列表
    if not discovered_teams:
        # 使用已知的 team slug -> squad_id
        teams_to_scrape = KNOWN_TEAMS
    else:
        teams_to_scrape = discovered_teams
    
    all_data = {}
    total_teams = len(teams_to_scrape)
    
    try:
        for idx, (team_slug, squad_id) in enumerate(sorted(teams_to_scrape.items())):
            url = team_url(squad_id, team_slug)
            team_display = team_slug.replace("-", " ")
            print(f"\n[{idx+1}/{total_teams}] {team_display}...")
            print(f"  URL: {url}")
            
            soup = fetch_page(url, driver)
            if not soup:
                print(f"  ❌ 页面获取失败")
                all_data[team_slug] = []
                time.sleep(3)
                continue
            
            # 提取各表格数据
            standard_rows = extract_table_from_soup(soup, "stats_standard")
            shooting_rows = extract_table_from_soup(soup, "stats_shooting")
            playing_time_rows = extract_table_from_soup(soup, "stats_playing_time")
            misc_rows = extract_table_from_soup(soup, "stats_misc")
            
            n_std = len(standard_rows or [])
            n_sh = len(shooting_rows or [])
            n_pt = len(playing_time_rows or [])
            n_misc = len(misc_rows or [])
            
            # 合并数据
            players = merge_player_data(standard_rows, shooting_rows, playing_time_rows, misc_rows)
            all_data[team_slug] = players
            
            print(f"  ✓ {len(players)} 人 | Std:{n_std} Shoot:{n_sh} PT:{n_pt} Misc:{n_misc}")
            
            # 打印前2名球员
            top = sorted(players, key=lambda x: x.get("gls", 0), reverse=True)[:2]
            for p in top:
                sh = p.get("sh", 0)
                sot = p.get("sot", 0)
                print(f"    {p['player']:22s} Gls:{p['gls']:2d} Sh:{sh:3d} SoT:{sot:3d} "
                      f"MP:{p['mp']:2d} Min:{p['min']:4d} PK:{p['pk']}/{p['pkatt']}")
            
            # 间隔请求，避免被封
            time.sleep(3)
            
            # 每10支球队保存一次进度
            if (idx + 1) % 10 == 0:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                print(f"  [进度保存] {idx+1}/{total_teams}")
    
    finally:
        driver.quit()
        print("\nChrome 已关闭")
        # 清理临时 profile
        if os.path.exists(TEMP_PROFILE_PATH):
            try:
                shutil.rmtree(TEMP_PROFILE_PATH)
            except:
                pass
    
    # 最终保存
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    # 输出摘要
    print(f"\n{'='*60}")
    print(f"爬取完成！输出: {output_path}")
    print(f"{'='*60}")
    total_players = 0
    with_shots = 0
    for team_slug, players in all_data.items():
        count = len(players)
        total_players += count
        sh_count = sum(1 for p in players if p.get("sh", 0) > 0)
        with_shots += sh_count
        status = "OK" if count > 0 else "EMPTY"
        print(f"  {team_slug:25s}: {count:3d} 人 ({sh_count} 人有射门数据) [{status}]")
    print(f"\n总计: {total_players} 名球员 / {len(all_data)} 支球队")
    print(f"有射门数据: {with_shots} 人")


if __name__ == "__main__":
    main()
