"""Official WC 2026 group-stage stadium assignments (FIFA draw, Dec 2025)."""
from __future__ import annotations

import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSIGNMENTS_PATH = os.path.join(ROOT, 'data', 'fixture_stadium_assignments.json')
VENUES_PATH = os.path.join(ROOT, 'data', 'stadium_venues.json')
TEAM_MAP_PATH = os.path.join(ROOT, 'data', 'team_name_map.json')

# (home_en, away_en, stadium_key) — FIFA group stage matches 1–72
_OFFICIAL_GROUP_STAGE = [
    ('Mexico', 'South Africa', 'azteca'),
    ('Korea Republic', 'Czechia', 'akron'),
    ('Canada', 'Bosnia-Herzegovina', 'bmo'),
    ('United States', 'Paraguay', 'sofi'),
    ('Haiti', 'Scotland', 'gillette'),
    ('Australia', 'Turkey', 'bcplace'),
    ('Brazil', 'Morocco', 'metlife'),
    ('Qatar', 'Switzerland', 'levis'),
    ('Ivory Coast', 'Ecuador', 'lincoln'),
    ('Germany', 'Curaçao', 'nrg'),
    ('Netherlands', 'Japan', 'att'),
    ('Sweden', 'Tunisia', 'bbva'),
    ('Saudi Arabia', 'Uruguay', 'hardrock'),
    ('Spain', 'Cape Verde Islands', 'mercedes_atlanta'),
    ('Iran', 'New Zealand', 'sofi'),
    ('Belgium', 'Egypt', 'lumen'),
    ('France', 'Senegal', 'metlife'),
    ('Iraq', 'Norway', 'gillette'),
    ('Argentina', 'Algeria', 'arrowhead'),
    ('Austria', 'Jordan', 'levis'),
    ('Ghana', 'Panama', 'bmo'),
    ('England', 'Croatia', 'att'),
    ('Portugal', 'Congo DR', 'nrg'),
    ('Uzbekistan', 'Colombia', 'azteca'),
    ('Czechia', 'South Africa', 'mercedes_atlanta'),
    ('Switzerland', 'Bosnia-Herzegovina', 'sofi'),
    ('Canada', 'Qatar', 'bcplace'),
    ('Mexico', 'Korea Republic', 'akron'),
    ('Brazil', 'Haiti', 'lincoln'),
    ('Scotland', 'Morocco', 'gillette'),
    ('Turkey', 'Paraguay', 'levis'),
    ('United States', 'Australia', 'lumen'),
    ('Germany', 'Ivory Coast', 'bmo'),
    ('Ecuador', 'Curaçao', 'arrowhead'),
    ('Netherlands', 'Sweden', 'nrg'),
    ('Tunisia', 'Japan', 'bbva'),
    ('Uruguay', 'Cape Verde Islands', 'hardrock'),
    ('Spain', 'Saudi Arabia', 'mercedes_atlanta'),
    ('Belgium', 'Iran', 'sofi'),
    ('New Zealand', 'Egypt', 'bcplace'),
    ('Norway', 'Senegal', 'metlife'),
    ('France', 'Iraq', 'lincoln'),
    ('Argentina', 'Austria', 'att'),
    ('Jordan', 'Algeria', 'levis'),
    ('England', 'Ghana', 'gillette'),
    ('Panama', 'Croatia', 'bmo'),
    ('Portugal', 'Uzbekistan', 'nrg'),
    ('Colombia', 'Congo DR', 'akron'),
    ('Scotland', 'Brazil', 'hardrock'),
    ('Morocco', 'Haiti', 'mercedes_atlanta'),
    ('Switzerland', 'Canada', 'bcplace'),
    ('Bosnia-Herzegovina', 'Qatar', 'lumen'),
    ('Czechia', 'Mexico', 'azteca'),
    ('South Africa', 'Korea Republic', 'bbva'),
    ('Curaçao', 'Ivory Coast', 'lincoln'),
    ('Ecuador', 'Germany', 'metlife'),
    ('Japan', 'Sweden', 'att'),
    ('Tunisia', 'Netherlands', 'arrowhead'),
    ('Turkey', 'United States', 'sofi'),
    ('Paraguay', 'Australia', 'levis'),
    ('Norway', 'France', 'gillette'),
    ('Senegal', 'Iraq', 'bmo'),
    ('Egypt', 'Iran', 'lumen'),
    ('New Zealand', 'Belgium', 'bcplace'),
    ('Cape Verde Islands', 'Saudi Arabia', 'nrg'),
    ('Uruguay', 'Spain', 'akron'),
    ('Panama', 'England', 'metlife'),
    ('Croatia', 'Ghana', 'lincoln'),
    ('Algeria', 'Austria', 'arrowhead'),
    ('Jordan', 'Argentina', 'att'),
    ('Colombia', 'Portugal', 'hardrock'),
    ('Congo DR', 'Uzbekistan', 'mercedes_atlanta'),
]

_TEAM_ALIASES = {
    'south korea': 'Korea Republic',
    'korea republic': 'Korea Republic',
    'usa': 'United States',
    'united states': 'United States',
    'bosnia and herzegovina': 'Bosnia-Herzegovina',
    'bosnia-herzegovina': 'Bosnia-Herzegovina',
    'cote divoire': 'Ivory Coast',
    'côte divoire': 'Ivory Coast',
    'ivory coast': 'Ivory Coast',
    'cape verde': 'Cape Verde Islands',
    'curacao': 'Curaçao',
    'turkiye': 'Turkey',
    'türkiye': 'Turkey',
    'congo dr': 'Congo DR',
    'dr congo': 'Congo DR',
    'czech republic': 'Czechia',
}


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _norm_team(name: str | None) -> str:
    if not name:
        return ''
    s = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', '', s.lower()).strip()
    return _TEAM_ALIASES.get(s, name)


def _cn_to_en(team_map: dict) -> dict[str, str]:
    return {cn: en for en, cn in team_map.items()}


def _en_to_cn(name_en: str, team_map: dict) -> str | None:
    if name_en in team_map:
        return team_map[name_en]
    for en, cn in team_map.items():
        if _norm_team(en) == _norm_team(name_en):
            return cn
    return None


def _stadium_fields(stadium_key: str, venues: dict) -> dict:
    v = venues.get(stadium_key) or {}
    label = v.get('label') or stadium_key
    return {
        'stadium_key': stadium_key,
        'stadium': label,
        'stadium_photo': f'{stadium_key}.jpg',
    }


def build_assignments_payload(team_map: dict | None = None, venues: dict | None = None) -> dict:
    team_map = team_map or load_json(TEAM_MAP_PATH, {})
    venues = venues or load_json(VENUES_PATH, {})
    by_match: dict[str, dict] = {}
    rows = []
    for i, (home_en, away_en, stadium_key) in enumerate(_OFFICIAL_GROUP_STAGE, start=1):
        home_cn = _en_to_cn(home_en, team_map)
        away_cn = _en_to_cn(away_en, team_map)
        if not home_cn or not away_cn:
            raise ValueError(f'unmapped teams: {home_en} vs {away_en}')
        fields = _stadium_fields(stadium_key, venues)
        match_key = f'{home_cn}|{away_cn}'
        row = {
            'official_match_no': i,
            'home_team': home_cn,
            'away_team': away_cn,
            'home_team_api': home_en,
            'away_team_api': away_en,
            **fields,
        }
        by_match[match_key] = row
        rows.append(row)
    return {
        'source': 'FIFA World Cup 2026 group stage (draw Dec 2025)',
        'note': 'Keyed by home|away CN team names; 72 group matches.',
        'by_match': by_match,
        'rows': rows,
    }


def save_assignments(path: str = ASSIGNMENTS_PATH) -> dict:
    payload = build_assignments_payload()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def load_assignments(path: str = ASSIGNMENTS_PATH) -> dict:
    data = load_json(path)
    if data and data.get('by_match'):
        return data
    return save_assignments(path)


def match_key(home_cn: str, away_cn: str) -> str:
    return f'{home_cn}|{away_cn}'


def lookup_stadium(home_cn: str, away_cn: str, assignments: dict | None = None) -> dict | None:
    assignments = assignments or load_assignments()
    return (assignments.get('by_match') or {}).get(match_key(home_cn, away_cn))


def apply_stadium_to_fixture(fixture: dict, assignments: dict | None = None) -> dict:
    """Set stadium / stadium_photo / stadium_key on a fixture dict when known."""
    home = fixture.get('home_team')
    away = fixture.get('away_team')
    if not home or not away:
        return fixture
    hit = lookup_stadium(home, away, assignments)
    if not hit:
        return fixture
    fixture = dict(fixture)
    fixture['stadium'] = hit['stadium']
    fixture['stadium_photo'] = hit['stadium_photo']
    if fixture.get('venue_context') is not None:
        vc = dict(fixture.get('venue_context') or {})
        vc['stadium_key'] = hit['stadium_key']
        fixture['venue_context'] = vc
    return fixture


def apply_stadiums_to_fixtures(fixtures: list, assignments: dict | None = None) -> tuple[list, int]:
    assignments = assignments or load_assignments()
    out = []
    applied = 0
    for f in fixtures:
        patched = apply_stadium_to_fixture(f, assignments)
        if patched.get('stadium_photo') != f.get('stadium_photo'):
            applied += 1
        out.append(patched)
    return out, applied
