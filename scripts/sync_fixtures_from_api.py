#!/usr/bin/env python3
"""Sync fixtures_2026.json from football-data.org WC API (utcDate -> Beijing time)."""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.secrets import read_secret
from briefing.fixture_stadiums import apply_stadium_to_fixture, apply_stadiums_to_fixtures, load_assignments
from briefing.venue_travel import enrich_fixtures
from briefing.stadium_assets import resolve_stadium_label, resolve_stadium_photo
from briefing.time_utils import beijing_date_from_utc, beijing_datetime_str
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from generate_fixtures_2026 import FLAG_CODES, STADIUM_BY_GROUP

WC_API = 'https://api.football-data.org/v4/competitions/WC/matches'
OUT_PATH = os.path.join(ROOT, 'data', 'fixtures_2026.json')
TEAM_MAP_PATH = os.path.join(ROOT, 'data', 'team_name_map.json')
CONFIG_PATH = os.path.join(ROOT, 'data', 'scraper_config.json')

STAGE_LABEL = {
    'GROUP_STAGE': 'group',
    'LAST_32': 'last_32',
    'LAST_16': 'round_16',
    'QUARTER_FINALS': 'quarter',
    'SEMI_FINALS': 'semi',
    'THIRD_PLACE': 'third_place',
    'FINAL': 'final',
}


def load_team_map():
    with open(TEAM_MAP_PATH, encoding='utf-8') as f:
        base = json.load(f)
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, encoding='utf-8') as f:
            cfg = json.load(f)
        base.update(cfg.get('team_name_map') or {})
    return base


def fetch_matches(token, season=2026):
    url = f'{WC_API}?season={season}'
    req = urllib.request.Request(url, headers={'X-Auth-Token': token})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return data.get('matches', [])


def parse_group(group_str):
    if not group_str:
        return None
    if group_str.startswith('GROUP_'):
        return group_str.replace('GROUP_', '')
    return group_str


def team_cn(en_name, team_map):
    if not en_name:
        return None
    return team_map.get(en_name)


def stadium_for_group(group):
    if group and group in STADIUM_BY_GROUP:
        stadium, photo = STADIUM_BY_GROUP[group]
        return stadium, photo
    return 'TBD', 'azteca.jpg'


def api_match_to_fixture(api_match, fixture_id, team_map):
    home_en = api_match['homeTeam'].get('name')
    away_en = api_match['awayTeam'].get('name')
    home = team_cn(home_en, team_map)
    away = team_cn(away_en, team_map)
    if not home or not away:
        return None, f'unmapped: {home_en} vs {away_en}'

    utc = api_match.get('utcDate')
    kickoff = beijing_datetime_str(utc)
    played = beijing_date_from_utc(utc)
    group = parse_group(api_match.get('group'))
    stage = STAGE_LABEL.get(api_match.get('stage'), api_match.get('stage', '').lower())

    venue = api_match.get('venue') or {}
    if isinstance(venue, dict) and venue.get('name'):
        stadium = resolve_stadium_label(venue.get('name'), venue.get('city'))
        stadium_photo = resolve_stadium_photo(venue.get('name'))
    else:
        stadium, stadium_photo = stadium_for_group(group)

    row = {
        'fixture_id': fixture_id,
        'api_match_id': api_match.get('id'),
        'stage': stage,
        'group': group,
        'matchday': api_match.get('matchday'),
        'home_team': home,
        'away_team': away,
        'home_team_api': home_en,
        'away_team_api': away_en,
        'home_flag': FLAG_CODES.get(home, 'xx'),
        'away_flag': FLAG_CODES.get(away, 'xx'),
        'kickoff_beijing': kickoff,
        'played_date': played,
        'utc_date': utc,
        'stadium': stadium,
        'stadium_photo': stadium_photo,
        'weather': '—',
        'temp': '—',
    }
    assignments = load_assignments()
    row = apply_stadium_to_fixture(row, assignments)
    return row, None


def main():
    with open(CONFIG_PATH, encoding='utf-8') as f:
        config = json.load(f)
    token = read_secret(
        config.get('api_token_file', 'static/basedata/football-data.txt'),
        config.get('api_token_env', 'FOOTBALL_DATA_TOKEN'),
    )
    if not token:
        print('FAIL: football-data token not found')
        sys.exit(1)

    team_map = load_team_map()
    api_matches = sorted(fetch_matches(token), key=lambda m: m.get('utcDate') or '')

    fixtures = []
    errors = []
    fid = 1
    for m in api_matches:
        row, err = api_match_to_fixture(m, fid, team_map)
        if err:
            errors.append((m.get('stage'), err))
            continue
        fixtures.append(row)
        fid += 1

    skipped_knockout = sum(1 for st, _ in errors if st and st != 'GROUP_STAGE')
    skipped_group = len(errors) - skipped_knockout
    if skipped_knockout:
        print(f'INFO skipped {skipped_knockout} knockout placeholders (teams TBD)')
    if skipped_group:
        print(f'WARN skipped {skipped_group} group matches:')
        for _, e in errors[:5]:
            if 'unmapped' in e:
                print(' ', e)

    fixtures, _ = apply_stadiums_to_fixtures(fixtures)
    fixtures = enrich_fixtures(fixtures)

    out = {
        'competition': 'FIFA World Cup 2026',
        'timezone': 'Asia/Shanghai',
        'source': 'football-data.org',
        'synced_from': 'GET /v4/competitions/WC/matches?season=2026',
        'stadium_assignments': 'data/fixture_stadium_assignments.json',
        'fixtures': fixtures,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    from briefing_data import fixtures_on_date
    print(f'Wrote {len(fixtures)} fixtures to {OUT_PATH}')
    for d in ('2026-06-11', '2026-06-12', '2026-06-13'):
        print(f'  Beijing {d}: {len(fixtures_on_date(fixtures, d))} matches')
    if skipped_group:
        sys.exit(1)


if __name__ == '__main__':
    main()
