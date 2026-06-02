"""
Fetch jersey numbers from FBref squad pages using Chrome profile cookies.
Follows the same pattern as fetch_fbref_wcq_data_v2.py which works.
"""
import os, sys, json, time, shutil, tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup, Comment
import unicodedata

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")

CHROME_PROFILE_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
TEMP_PROFILE_PATH = os.path.join(tempfile.gettempdir(), "chrome_selenium_profile")

TEAMS = {
    "Mexico":("b009a548","Mexico"),"South Africa":("7a37bb04","South-Africa"),
    "Korea Republic":("473f0fbf","Korea-Republic"),"Czech Republic":("e86ba5fc","Czech-Republic"),
    "Canada":("ae7a7eae","Canada"),"Bosnia-Herzegovina":("d99ad29f","Bosnia-Herzegovina"),
    "Qatar":("607a71be","Qatar"),"Switzerland":("81021a70","Switzerland"),
    "Brazil":("304635c3","Brazil"),"Morocco":("fb9480a2","Morocco"),
    "Haiti":("8acbbf02","Haiti"),"Scotland":("602d3994","Scotland"),
    "United States":("0f66725b","United-States"),"Paraguay":("d2043442","Paraguay"),
    "Australia":("b384a8ce","Australia"),"Turkey":("f1b0042d","Turkiye"),
    "Germany":("c1e40422","Germany"),"Curacao":("7425e4dd","Curacao"),
    "Ivory Coast":("534b07cb","Cote-dIvoire"),"Ecuador":("123acaf8","Ecuador"),
    "Netherlands":("5bb5024a","Netherlands"),"Japan":("ffcf1690","Japan"),
    "Sweden":("82b0baa4","Sweden"),"Tunisia":("9f63b82e","Tunisia"),
    "Belgium":("361422b9","Belgium"),"Egypt":("7165f5af","Egypt"),
    "Iran":("6e80f01f","Iran"),"New Zealand":("ae3466f8","New-Zealand"),
    "Spain":("b561dd30","Spain"),"Cape Verde":("63328f64","Cape-Verde"),
    "Saudi Arabia":("2d9c7a24","Saudi-Arabia"),"Uruguay":("870e020f","Uruguay"),
    "France":("b1b36dcd","France"),"Senegal":("2a08ef61","Senegal"),
    "Iraq":("a26c9725","Iraq"),"Norway":("599eba19","Norway"),
    "Argentina":("f9fddd6e","Argentina"),"Algeria":("5601b6b7","Algeria"),
    "Austria":("68f4e4e4","Austria"),"Jordan":("e4ba3c7b","Jordan"),
    "Portugal":("4a1b4ea8","Portugal"),"DR Congo":("ce21a768","DR-Congo"),
    "Uzbekistan":("407e8eb3","Uzbekistan"),"Colombia":("ab73cfe5","Colombia"),
    "England":("1862c019","England"),"Croatia":("7b08e376","Croatia"),
    "Ghana":("cf8f5961","Ghana"),"Panama":("a65b1585","Panama"),
}

TEAM_CN = {
    "Mexico":"墨西哥","South Africa":"南非","Korea Republic":"韩国",
    "Czech Republic":"捷克","Canada":"加拿大","Bosnia-Herzegovina":"波黑",
    "Qatar":"卡塔尔","Switzerland":"瑞士","Brazil":"巴西",
    "Morocco":"摩洛哥","Haiti":"海地","Scotland":"苏格兰",
    "United States":"美国","Paraguay":"巴拉圭","Australia":"澳大利亚",
    "Turkey":"土耳其","Germany":"德国","Curacao":"库拉索",
    "Ivory Coast":"科特迪瓦","Ecuador":"厄瓜多尔","Netherlands":"荷兰",
    "Japan":"日本","Sweden":"瑞典","Tunisia":"突尼斯",
    "Belgium":"比利时","Egypt":"埃及","Iran":"伊朗",
    "New Zealand":"新西兰","Spain":"西班牙","Cape Verde":"佛得角",
    "Saudi Arabia":"沙特","Uruguay":"乌拉圭","France":"法国",
    "Senegal":"塞内加尔","Iraq":"伊拉克","Norway":"挪威",
    "Argentina":"阿根廷","Algeria":"阿尔及利亚","Austria":"奥地利",
    "Jordan":"约旦","Portugal":"葡萄牙","DR Congo":"刚果（金）",
    "Uzbekistan":"乌兹别克斯坦","Colombia":"哥伦比亚","England":"英格兰",
    "Croatia":"克罗地亚","Ghana":"加纳","Panama":"巴拿马",
}

def norm(name):
    nfkd = unicodedata.normalize('NFKD', name.lower().strip())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def copy_profile():
    if not os.path.exists(CHROME_PROFILE_PATH):
        return False
    dd = os.path.join(CHROME_PROFILE_PATH, "Default")
    if not os.path.exists(dd):
        return False
    if os.path.exists(TEMP_PROFILE_PATH):
        try: shutil.rmtree(TEMP_PROFILE_PATH)
        except:
            try:
                old = TEMP_PROFILE_PATH + "_old"
                if os.path.exists(old): shutil.rmtree(old, ignore_errors=True)
                os.rename(TEMP_PROFILE_PATH, old)
            except: pass
    dest = os.path.join(TEMP_PROFILE_PATH, "Default")
    os.makedirs(dest, exist_ok=True)
    ls = os.path.join(CHROME_PROFILE_PATH, "Local State")
    if os.path.exists(ls): shutil.copy2(ls, os.path.join(TEMP_PROFILE_PATH, "Local State"))
    for f in ["Cookies","Cookies-journal","Preferences","Secure Preferences"]:
        s = os.path.join(dd, f)
        if os.path.exists(s): shutil.copy2(s, os.path.join(dest, f))
    for d in ["Local Storage","IndexedDB"]:
        s = os.path.join(dd, d)
        t = os.path.join(dest, d)
        if os.path.exists(s):
            if os.path.exists(t): shutil.rmtree(t, ignore_errors=True)
            try: shutil.copytree(s, t, ignore_dangling_symlinks=True)
            except: pass
    return True

def get_numbers(driver):
    """Extract player -> jersey from the standard stats table on current page"""
    src = driver.page_source
    soup = BeautifulSoup(src, "html.parser")
    table = soup.find("table", id=lambda x: x and x.startswith("stats_standard"))
    if not table:
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            if "stats_standard" in c:
                cs = BeautifulSoup(c, "html.parser")
                table = cs.find("table", id=lambda x: x and x.startswith("stats_standard"))
                if table: break
    if not table: return {}
    result = {}
    tbody = table.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            if tr.get("class") and "thead" in tr.get("class", []): continue
            ne = tr.find("th", {"data-stat": "player"})
            nu = tr.find("td", {"data-stat": "number"})
            if ne and nu:
                n = ne.get_text(strip=True)
                v = nu.get_text(strip=True)
                if n and v: result[norm(n)] = int(v)
    return result

def main():
    copy_profile()
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox"); options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if os.path.exists(TEMP_PROFILE_PATH):
        options.add_argument(f"--user-data-dir={TEMP_PROFILE_PATH}")
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # Step 1: Pass Cloudflare on FBref homepage
    print("访问 FBref 首页通过 Cloudflare...", flush=True)
    driver.get("https://fbref.com")
    for i in range(30):
        time.sleep(3)
        src = driver.page_source
        if "Just a moment" in src or "安全验证" in src:
            if i % 5 == 0: print(f"  Cloudflare... ({(i+1)*3}s)", flush=True)
        elif len(src) > 50000:
            print(f"  ✅ Cloudflare 通过! ({(i+1)*3}s)", flush=True)
            break

    # Step 2: Fetch each team
    all_nums = {}; fails = []
    for idx, (eng, (sid, slug)) in enumerate(TEAMS.items(), 1):
        cn = TEAM_CN.get(eng, eng)
        url = f"https://fbref.com/en/squads/{sid}/{slug}-Men-Stats"
        print(f"[{idx}/48] {eng} ({cn})...", end=" ", flush=True)

        try:
            driver.get(url)
            time.sleep(5)
            # Wait for Cloudflare if needed
            for _ in range(15):
                src = driver.page_source
                if "Just a moment" in src or "安全验证" in src:
                    time.sleep(3)
                else:
                    break
            nums = get_numbers(driver)
            if nums:
                all_nums[cn] = nums
                print(f"{len(nums)} players ✓", flush=True)
            else:
                print(f"0 players ⚠", flush=True)
                fails.append(eng)
        except Exception as e:
            print(f"ERR: {e} ✗", flush=True)
            fails.append(eng)

    driver.quit()
    fp = os.path.join(DATA_DIR, "fbref_jersey_numbers.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(all_nums, f, ensure_ascii=False, indent=2)
    tp = sum(len(v) for v in all_nums.values())
    print(f"\n✅ {len(all_nums)} teams, {tp} players -> {fp}")
    if fails: print(f"⚠ Failed {len(fails)}: {', '.join(fails)}")

if __name__ == "__main__":
    main()
