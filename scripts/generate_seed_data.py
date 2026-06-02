"""
Generate updated seed_data.py with real 26-man squad names.
Parses Sky Sports squad data (with positions) and maps to Chinese team names.
"""
import re
import json
import os
import unicodedata

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)


def strip_accents(s):
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


# ── Re-parse Sky Sports text with positions ──
# (incorporating the SKY_SPORTS_TEXT from filter_by_squad.py)

def load_sky_text():
    """Load the sky sports text from the filter_by_squad.py file"""
    with open(os.path.join(SCRIPTS_DIR, 'filter_by_squad.py'), 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract the SKY_SPORTS_TEXT variable content
    match = re.search(r'SKY_SPORTS_TEXT\s*=\s*r?"""(.*?)"""', content, re.DOTALL)
    if match:
        return match.group(1)
    return None


def parse_squads_with_positions(text):
    """Parse Sky Sports squad text into dict: team_name -> {position: [player_names]}"""
    squads = {}
    
    # Split by team headers (### Team Name)
    teams_pattern = re.compile(r'###\s+(.+?)\n(.*?)(?=\n###|\Z)', re.DOTALL)
    
    for match in teams_pattern.finditer(text):
        team_name = match.group(1).strip()
        team_text = match.group(2).strip()
        
        team_players = {}
        # Extract player names from Goalkeepers:/Defenders:/Midfielders:/Forwards: sections
        section_pattern = re.compile(r'(Goalkeepers|Defenders|Midfielders|Forwards):(.*?)(?=\n\n|\Z|(?:Goalkeepers|Defenders|Midfielders|Forwards):)', re.DOTALL)
        
        for section_match in section_pattern.finditer(team_text):
            position = section_match.group(1)
            section_content = section_match.group(2)
            
            # Map position to short code
            pos_map = {
                'Goalkeepers': 'GK',
                'Defenders': 'DF',
                'Midfielders': 'MF',
                'Forwards': 'FW',
            }
            pos_code = pos_map.get(position, 'MF')
            
            # Extract individual player names
            player_pattern = re.compile(r'([^,;]+?)\s*\([^)]*\)')
            for p_match in player_pattern.finditer(section_content):
                player_name = p_match.group(1).strip()
                if player_name and player_name not in ['Also See:']:
                    team_players[strip_accents(player_name).lower()] = {
                        'name': player_name,
                        'position': pos_code,
                    }
        
        if team_players:
            squads[team_name] = team_players
    
    return squads


# ── Team name mapping: Sky Sports -> Chinese name in seed_data ──
TEAM_NAME_MAP = {
    "Mexico": "墨西哥",
    "South Africa": "南非",
    "South Korea": "韩国",
    "Czech Republic": "捷克",
    "Canada": "加拿大",
    "Bosnia-Herzegovina": "波黑",
    "Qatar": "卡塔尔",
    "Switzerland": "瑞士",
    "Brazil": "巴西",
    "Morocco": "摩洛哥",
    "Haiti": "海地",
    "Scotland": "苏格兰",
    "USA": "美国",
    "Paraguay": "巴拉圭",
    "Australia": "澳大利亚",
    "Turkey": "土耳其",
    "Germany": "德国",
    "Curacao": "库拉索",
    "Ivory Coast": "科特迪瓦",
    "Ecuador": "厄瓜多尔",
    "Netherlands": "荷兰",
    "Japan": "日本",
    "Sweden": "瑞典",
    "Tunisia": "突尼斯",
    "Belgium": "比利时",
    "Egypt": "埃及",
    "Iran": "伊朗",
    "New Zealand": "新西兰",
    "Spain": "西班牙",
    "Cape Verde": "佛得角",
    "Saudi Arabia": "沙特",
    "Uruguay": "乌拉圭",
    "France": "法国",
    "Senegal": "塞内加尔",
    "Iraq": "伊拉克",
    "Norway": "挪威",
    "Argentina": "阿根廷",
    "Algeria": "阿尔及利亚",
    "Austria": "奥地利",
    "Jordan": "约旦",
    "Portugal": "葡萄牙",
    "DR Congo": "刚果（金）",
    "Uzbekistan": "乌兹别克斯坦",
    "Colombia": "哥伦比亚",
    "England": "英格兰",
    "Croatia": "克罗地亚",
    "Ghana": "加纳",
    "Panama": "巴拿马",
}


# ── Existing seed_data team groups for reference ──
def get_teams_list():
    """Return the TEAMS list from seed_data.py"""
    return [
        # Group A
        ('墨西哥', 'A', '\U0001f1f2\U0001f1fd'),
        ('捷克', 'A', '\U0001f1e8\U0001f1ff'),
        ('南非', 'A', '\U0001f1ff\U0001f1e6'),
        ('韩国', 'A', '\U0001f1f0\U0001f1f7'),
        # Group B
        ('加拿大', 'B', '\U0001f1e8\U0001f1e6'),
        ('波黑', 'B', '\U0001f1e7\U0001f1e6'),
        ('卡塔尔', 'B', '\U0001f1f6\U0001f1e6'),
        ('瑞士', 'B', '\U0001f1e8\U0001f1ed'),
        # Group C
        ('巴西', 'C', '\U0001f1e7\U0001f1f7'),
        ('海地', 'C', '\U0001f1ed\U0001f1f9'),
        ('摩洛哥', 'C', '\U0001f1f2\U0001f1e6'),
        ('苏格兰', 'C', '\U0001f3f4\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f'),
        # Group D
        ('美国', 'D', '\U0001f1fa\U0001f1f8'),
        ('澳大利亚', 'D', '\U0001f1e6\U0001f1fa'),
        ('巴拉圭', 'D', '\U0001f1f5\U0001f1fe'),
        ('土耳其', 'D', '\U0001f1f9\U0001f1f7'),
        # Group E
        ('库拉索', 'E', '\U0001f1e8\U0001f1fc'),
        ('厄瓜多尔', 'E', '\U0001f1ea\U0001f1e8'),
        ('德国', 'E', '\U0001f1e9\U0001f1ea'),
        ('科特迪瓦', 'E', '\U0001f1e8\U0001f1ee'),
        # Group F
        ('荷兰', 'F', '\U0001f1f3\U0001f1f1'),
        ('日本', 'F', '\U0001f1ef\U0001f1f5'),
        ('瑞典', 'F', '\U0001f1f8\U0001f1ea'),
        ('突尼斯', 'F', '\U0001f1f9\U0001f1f3'),
        # Group G
        ('比利时', 'G', '\U0001f1e7\U0001f1ea'),
        ('埃及', 'G', '\U0001f1ea\U0001f1ec'),
        ('伊朗', 'G', '\U0001f1ee\U0001f1f7'),
        ('新西兰', 'G', '\U0001f1f3\U0001f1ff'),
        # Group H
        ('佛得角', 'H', '\U0001f1e8\U0001f1fb'),
        ('沙特', 'H', '\U0001f1f8\U0001f1e6'),
        ('西班牙', 'H', '\U0001f1ea\U0001f1f8'),
        ('乌拉圭', 'H', '\U0001f1fa\U0001f1fe'),
        # Group I
        ('法国', 'I', '\U0001f1eb\U0001f1f7'),
        ('挪威', 'I', '\U0001f1f3\U0001f1f4'),
        ('塞内加尔', 'I', '\U0001f1f8\U0001f1f3'),
        ('伊拉克', 'I', '\U0001f1ee\U0001f1f6'),
        # Group J
        ('阿尔及利亚', 'J', '\U0001f1e9\U0001f1ff'),
        ('阿根廷', 'J', '\U0001f1e6\U0001f1f7'),
        ('奥地利', 'J', '\U0001f1e6\U0001f1f9'),
        ('约旦', 'J', '\U0001f1ef\U0001f1f4'),
        # Group K
        ('哥伦比亚', 'K', '\U0001f1e8\U0001f1f4'),
        ('刚果（金）', 'K', '\U0001f1e8\U0001f1e9'),
        ('葡萄牙', 'K', '\U0001f1f5\U0001f1f9'),
        ('乌兹别克斯坦', 'K', '\U0001f1fa\U0001f1ff'),
        # Group L
        ('克罗地亚', 'L', '\U0001f1ed\U0001f1f7'),
        ('英格兰', 'L', '\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f'),
        ('加纳', 'L', '\U0001f1ec\U0001f1ed'),
        ('巴拿马', 'L', '\U0001f1f5\U0001f1e6'),
    ]


def normalize(name):
    return strip_accents(name).lower().strip()


def load_existing_players():
    """Load existing PLAYERS_DATA from seed_data.py to preserve Chinese names"""
    existing = {}
    seed_path = os.path.join(ROOT_DIR, 'seed_data.py')
    if not os.path.exists(seed_path):
        return existing

    with open(seed_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Try to extract PLAYERS_DATA dict
    import ast
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'PLAYERS_DATA':
                        if isinstance(node.value, ast.Dict):
                            for key, val in zip(node.value.keys, node.value.values):
                                if isinstance(val, ast.List):
                                    team_name = ast.literal_eval(key)
                                    team_players = {}
                                    for item in val.elts:
                                        if isinstance(item, ast.Tuple) and len(item.elts) >= 4:
                                            name = ast.literal_eval(item.elts[0])
                                            name_cn = ast.literal_eval(item.elts[1])
                                            team_players[name.lower()] = name_cn
                                    existing[team_name] = team_players
    except Exception as e:
        print(f"  ⚠ Warning: could not parse existing seed_data.py: {e}")

    return existing


def main():
    # Load Sky Sports text
    text = load_sky_text()
    if not text:
        print("ERROR: Could not extract SKY_SPORTS_TEXT from filter_by_squad.py")
        return
    
    # Parse squads with positions
    squads = parse_squads_with_positions(text)
    print(f"Parsed {len(squads)} teams from Sky Sports data")
    
    # Build team players data: Chinese name -> [(player_name, position, jersey)]
    teams = get_teams_list()
    team_players_data = {}
    team_flag_map = {}
    
    for cn_name, group, flag in teams:
        team_flag_map[cn_name] = flag
        
        # Find matching Sky Sports team name
        sky_name = None
        for sk, cn in TEAM_NAME_MAP.items():
            if cn == cn_name:
                sky_name = sk
                break
        
        if sky_name and sky_name in squads:
            players = list(squads[sky_name].values())
            # Sort: GK first, then DF, MF, FW
            pos_order = {'GK': 0, 'DF': 1, 'MF': 2, 'FW': 3}
            players.sort(key=lambda p: pos_order.get(p['position'], 99))
            
            team_players_data[cn_name] = players
            print(f"  {cn_name} ({sky_name}): {len(players)} players")
        else:
            print(f"  ⚠ {cn_name}: no matching squad data (sky_name={sky_name})")
            team_players_data[cn_name] = []
    
    # ── Generate updated seed_data.py ──
    lines = []
    lines.append('from models import get_db, init_db')
    lines.append('')
    lines.append('')
    lines.append('# 48 teams in 12 groups (A-L), 4 per group')
    lines.append('# Actual 2026 FIFA World Cup qualified teams')
    lines.append('TEAMS = [')
    for cn_name, group, flag in teams:
        lines.append(f"    ('{cn_name}', '{group}', '{flag}'),")
    lines.append(']')
    lines.append('')
    
    # Generate PLAYERS_DATA
    # Load existing Chinese names to preserve them
    existing_players = load_existing_players()
    
    lines.append('')
    lines.append('# 26-man squad for each team: (name, name_cn, jersey_number, position)')
    lines.append('# position: GK/DF/MF/FW')
    lines.append('# name_cn: Chinese display name (empty string = use English)')
    lines.append('PLAYERS_DATA = {')
    
    for cn_name, group, flag in teams:
        players = team_players_data.get(cn_name, [])
        existing_team = existing_players.get(cn_name, {})
        lines.append(f"    '{cn_name}': [")
        for i, p in enumerate(players, 1):
            name = p['name']
            pos = p['position']
            # Preserve existing Chinese name, or leave empty
            name_cn = existing_team.get(name.lower(), '')
            # Escape single quotes in names
            escaped_name = name.replace("'", "\\'")
            escaped_name_cn = name_cn.replace("'", "\\'")
            lines.append(f"        ('{escaped_name}', '{escaped_name_cn}', {i}, '{pos}'),")
        lines.append('    ],')
    
    lines.append('}')
    lines.append('')
    
    # Generate seed_database function
    lines.append('')
    lines.append('')
    lines.append('def seed_database():')
    lines.append('    init_db()')
    lines.append('    db = get_db()')
    lines.append('    cur = db.cursor()')
    lines.append('')
    lines.append('    # Insert teams')
    lines.append('    team_ids = {}')
    lines.append('    for i, (name, group, flag) in enumerate(TEAMS, 1):')
    lines.append("        cur.execute('INSERT INTO teams (name, group_name, flag_emoji) VALUES (?, ?, ?)', (name, group, flag))")
    lines.append('        team_ids[i] = cur.lastrowid')
    lines.append('')
    lines.append('    # Insert players (26 per team from real WC squads)')
    lines.append('    player_count = 0')
    lines.append('    for team_idx in range(1, 49):')
    lines.append('        team_id = team_ids[team_idx]')
    lines.append('        cn_name = TEAMS[team_idx - 1][0]')
    lines.append("        squad = PLAYERS_DATA.get(cn_name, [])")
    lines.append('        for p in squad:')
    lines.append("            name, name_cn, jersey_number, position = p")
    lines.append("            cur.execute('INSERT INTO players (name, name_cn, jersey_number, team_id, position) VALUES (?, ?, ?, ?, ?)', (name, name_cn, jersey_number, team_id, position))")
    lines.append('            player_count += 1')
    lines.append('')
    lines.append('    # Insert participants')
    lines.append('    participants = [')
    lines.append("        ('庆爷', 1),")
    lines.append("        ('耗子', 2),")
    lines.append("        ('老王', 3),")
    lines.append("        ('李总', 4),")
    lines.append("        ('老闫', 5),")
    lines.append('    ]')
    lines.append('    for name, order in participants:')
    lines.append("        cur.execute('INSERT INTO participants (name, draft_order) VALUES (?, ?)', (name, order))")
    lines.append('')
    lines.append('    db.commit()')
    lines.append('    db.close()')
    lines.append("    print(f'Seeded: {len(TEAMS)} teams, {player_count} players, {len(participants)} participants')")
    lines.append('')
    lines.append('')
    lines.append("if __name__ == '__main__':")
    lines.append('    seed_database()')
    
    # Write output
    output_path = os.path.join(ROOT_DIR, 'seed_data.py')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n✅ seed_data.py generated: {output_path}")
    print(f"   Teams: {len(teams)}")
    total_players = sum(len(v) for v in team_players_data.values())
    print(f"   Players: {total_players}")


if __name__ == "__main__":
    main()
