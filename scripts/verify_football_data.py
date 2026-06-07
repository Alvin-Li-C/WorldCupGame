#!/usr/bin/env python3
"""Verify football-data.org WC API access and Beijing date mapping."""
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.secrets import read_secret
from briefing.time_utils import beijing_date_from_utc, beijing_datetime_str, utc_to_bj

def load_team_map():
    config_path = os.path.join(ROOT, 'data', 'scraper_config.json')
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)
    rel = config.get('team_name_map_file', 'data/team_name_map.json')
    path = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    with open(path, encoding='utf-8') as f:
        base = json.load(f)
    base.update(config.get('team_name_map') or {})
    return base


def fetch_json(url, token):
    req = urllib.request.Request(url, headers={'X-Auth-Token': token})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    config_path = os.path.join(ROOT, 'data', 'scraper_config.json')
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)
    team_map = load_team_map()
    token = read_secret(config.get('api_token_file', ''), config.get('api_token_env'))
    if not token:
        print('FAIL: football-data token not found')
        sys.exit(1)

    errors = []

    # Wrong endpoint (legacy) — expect 0 WC matches in response for a random day
    bad_url = 'https://api.football-data.org/v4/matches?dateFrom=2026-06-11&dateTo=2026-06-11'
    try:
        bad = fetch_json(bad_url, token)
        wc_bad = [m for m in bad.get('matches', []) if m.get('competition', {}).get('code') == 'WC']
        print(f'legacy /matches date filter: total={len(bad.get("matches", []))} wc={len(wc_bad)}')
    except urllib.error.HTTPError as e:
        print(f'legacy endpoint HTTP {e.code}')
        errors.append(f'legacy endpoint: {e.code}')

    # Correct WC endpoint
    good_url = 'https://api.football-data.org/v4/competitions/WC/matches?season=2026'
    data = fetch_json(good_url, token)
    matches = data.get('matches', [])
    finished = [m for m in matches if m.get('status') == 'FINISHED']
    print(f'WC /competitions/WC/matches season=2026: total={len(matches)} finished={len(finished)}')

    unmapped = set()
    for m in matches:
        for side in ('homeTeam', 'awayTeam'):
            en = m[side].get('name')
            if en and en not in team_map:
                unmapped.add(en)
    if unmapped:
        errors.append(f'unmapped teams: {sorted(unmapped)}')
        print('WARN unmapped:', sorted(unmapped))
    else:
        print('team_name_map: all 48 API teams covered')

    # Beijing date sample (opening match)
    if matches:
        sample = matches[0]
        utc = sample.get('utcDate')
        bj = beijing_datetime_str(utc)
        bj_date = beijing_date_from_utc(utc)
        print(f'sample: {sample["homeTeam"]["name"]} vs {sample["awayTeam"]["name"]}')
        print(f'  utcDate={utc}')
        print(f'  beijing={bj} 赛果日={bj_date}')
        if utc == '2026-06-11T19:00:00Z' and bj_date != '2026-06-12':
            errors.append('Beijing date conversion wrong for opening match')

    if errors:
        print('FAIL:', '; '.join(errors))
        sys.exit(1)
    print('OK: football-data WC API verified')


if __name__ == '__main__':
    main()
