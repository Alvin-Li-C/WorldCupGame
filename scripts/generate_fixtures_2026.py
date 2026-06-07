"""Generate data/fixtures_2026.json — DEPRECATED: use scripts/sync_fixtures_from_api.py instead.

Legacy generator produced incorrect schedules (24 matches on one Beijing day).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seed_data import TEAMS

STADIUM_BY_GROUP = {
    'A': ('Estadio Azteca · Mexico City', 'azteca.jpg'),
    'B': ('SoFi Stadium · Los Angeles', 'sofi.jpg'),
    'C': ('Estadio Azteca · Mexico City', 'azteca.jpg'),
    'D': ('SoFi Stadium · Los Angeles', 'sofi.jpg'),
    'E': ('Estadio Azteca · Mexico City', 'azteca.jpg'),
    'F': ('SoFi Stadium · Los Angeles', 'sofi.jpg'),
    'G': ('Estadio Azteca · Mexico City', 'azteca.jpg'),
    'H': ('SoFi Stadium · Los Angeles', 'sofi.jpg'),
    'I': ('Estadio Azteca · Mexico City', 'azteca.jpg'),
    'J': ('SoFi Stadium · Los Angeles', 'sofi.jpg'),
    'K': ('Estadio Azteca · Mexico City', 'azteca.jpg'),
    'L': ('SoFi Stadium · Los Angeles', 'sofi.jpg'),
}

# Group stage: Jun 11 – Jun 27 2026 (3 matchdays)
MATCHDAY_DATES = {
    1: '2026-06-11',
    2: '2026-06-18',
    3: '2026-06-25',
}
KICKOFFS = ['03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00', '22:00']

FLAG_CODES = {
    '墨西哥': 'mx', '捷克': 'cz', '南非': 'za', '韩国': 'kr', '加拿大': 'ca', '波黑': 'ba',
    '卡塔尔': 'qa', '瑞士': 'ch', '巴西': 'br', '海地': 'ht', '摩洛哥': 'ma', '苏格兰': 'gb-sct',
    '美国': 'us', '澳大利亚': 'au', '巴拉圭': 'py', '土耳其': 'tr', '库拉索': 'cw', '厄瓜多尔': 'ec',
    '德国': 'de', '科特迪瓦': 'ci', '荷兰': 'nl', '日本': 'jp', '瑞典': 'se', '突尼斯': 'tn',
    '比利时': 'be', '埃及': 'eg', '伊朗': 'ir', '新西兰': 'nz', '佛得角': 'cv', '沙特': 'sa',
    '西班牙': 'es', '乌拉圭': 'uy', '法国': 'fr', '挪威': 'no', '塞内加尔': 'sn', '伊拉克': 'iq',
    '阿尔及利亚': 'dz', '阿根廷': 'ar', '奥地利': 'at', '约旦': 'jo', '哥伦比亚': 'co',
    '刚果（金）': 'cd', '葡萄牙': 'pt', '乌兹别克斯坦': 'uz', '克罗地亚': 'hr', '英格兰': 'gb-eng',
    '加纳': 'gh', '巴拿马': 'pa',
}


def group_teams():
    groups = {}
    for name, group, _ in TEAMS:
        groups.setdefault(group, []).append(name)
    return groups


def round_robin_pairs(teams):
    """6 matches for 4 teams."""
    a, b, c, d = teams
    return [
        (a, b), (c, d),
        (a, c), (b, d),
        (a, d), (b, c),
    ]


def main():
    fixtures = []
    fid = 1
    kick_idx = 0
    for group in sorted(group_teams().keys()):
        teams = group_teams()[group]
        pairs = round_robin_pairs(teams)
        stadium, photo = STADIUM_BY_GROUP[group]
        for md in (1, 2, 3):
            date = MATCHDAY_DATES[md]
            for i in range(2):
                home, away = pairs[(md - 1) * 2 + i]
                kick = KICKOFFS[kick_idx % len(KICKOFFS)]
                kick_idx += 1
                fixtures.append({
                    'fixture_id': fid,
                    'stage': 'group',
                    'group': group,
                    'matchday': md,
                    'home_team': home,
                    'away_team': away,
                    'home_flag': FLAG_CODES.get(home, 'xx'),
                    'away_flag': FLAG_CODES.get(away, 'xx'),
                    'kickoff_beijing': f'{date} {kick}',
                    'played_date': date,
                    'stadium': stadium,
                    'stadium_photo': photo,
                    'weather': '多云',
                    'temp': '24°C',
                })
                fid += 1

    out = {
        'competition': 'FIFA World Cup 2026',
        'timezone': 'Asia/Shanghai',
        'fixtures': fixtures,
    }
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, 'data', 'fixtures_2026.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'Wrote {len(fixtures)} fixtures to {path}')


if __name__ == '__main__':
    main()
