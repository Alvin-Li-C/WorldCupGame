"""Build per-team recent form: WC finished matches + ESPN pre-tournament results."""
import json
import os
import time
import urllib.error
import urllib.request

from briefing.espn_api_form import build_team_form_api
from briefing.secrets import read_secret
from briefing.time_utils import beijing_date_from_utc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORM_PATH = os.path.join(ROOT, 'data', 'briefing', 'team_form.json')
ESPN_CACHE_PATH = os.path.join(ROOT, 'data', 'briefing', 'team_form_espn.json')
FORM_SEED_PATH = os.path.join(ROOT, 'data', 'team_form_seed.json')
WC_API = 'https://api.football-data.org/v4/competitions/WC/matches'
FORM_CUTOFF = '2026-06-11'


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_finished_wc(token, season=2026):
    if not token:
        return []
    url = f'{WC_API}?season={season}&status=FINISHED'
    req = urllib.request.Request(url, headers={'X-Auth-Token': token})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get('matches', [])
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return []


def api_team_to_cn(name, team_map):
    return team_map.get(name) if name else None


def result_char(team_cn, home_cn, away_cn, hs, aw):
    if hs is None or aw is None:
        return None
    if team_cn == home_cn:
        if hs > aw:
            return 'W'
        if hs < aw:
            return 'L'
        return 'D'
    if team_cn == away_cn:
        if aw > hs:
            return 'W'
        if aw < hs:
            return 'L'
        return 'D'
    return None


def build_team_form_wc(api_matches, team_map):
    """Last 5 finished WC 2026 matches per team (during tournament)."""
    timeline = {}
    for m in api_matches:
        if m.get('status') != 'FINISHED':
            continue
        home_cn = api_team_to_cn(m.get('homeTeam', {}).get('name'), team_map)
        away_cn = api_team_to_cn(m.get('awayTeam', {}).get('name'), team_map)
        if not home_cn or not away_cn:
            continue
        score = m.get('score', {}).get('fullTime') or {}
        hs, aw = score.get('home'), score.get('away')
        kick = m.get('utcDate', '')
        for team in (home_cn, away_cn):
            ch = result_char(team, home_cn, away_cn, hs, aw)
            if not ch:
                continue
            gf = hs if team == home_cn else aw
            ga = aw if team == home_cn else hs
            timeline.setdefault(team, []).append({
                'utc': kick,
                'char': ch,
                'gf': gf or 0,
                'ga': ga or 0,
            })

    out = {}
    for team, rows in timeline.items():
        rows.sort(key=lambda r: r['utc'], reverse=True)
        last5 = rows[:5]
        if not last5:
            continue
        out[team] = {
            'last5': ''.join(r['char'] for r in reversed(last5)),
            'goals_for': sum(r['gf'] for r in last5),
            'goals_against': sum(r['ga'] for r in last5),
            'updated_at': beijing_date_from_utc(last5[0]['utc']) if last5[0].get('utc') else None,
            'source': 'football-data-wc',
        }
    return out


def fetch_espn_form(cutoff_date=FORM_CUTOFF):
    cached = load_json(ESPN_CACHE_PATH, {})
    if isinstance(cached, dict) and len(cached) >= 40:
        return cached

    print('espn-api: fetching team schedules...', flush=True)
    out = build_team_form_api(cutoff_date=cutoff_date)
    if out:
        save_json(ESPN_CACHE_PATH, out)
    return out


def _merge_seed_row(api_row, seed_row):
    if not seed_row:
        return api_row
    if not api_row:
        return dict(seed_row)
    row = dict(api_row)
    for key in ('last5', 'goals_for', 'goals_against', 'updated_at', 'source'):
        if not row.get(key) and seed_row.get(key):
            row[key] = seed_row[key]
    if not row.get('wcq') and seed_row.get('wcq'):
        row['wcq'] = seed_row['wcq']
    return row


def merge_form(wc_form, espn_form, seed_form=None):
    """Seed < ESPN pre-tournament < WC results (during tournament)."""
    out = {}
    teams = set(seed_form or {}) | set(espn_form or {}) | set(wc_form or {})
    for team in teams:
        row = _merge_seed_row((espn_form or {}).get(team), (seed_form or {}).get(team))
        wc_row = (wc_form or {}).get(team)
        if wc_row and wc_row.get('last5'):
            row = wc_row
            seed_wcq = (seed_form or {}).get(team, {}).get('wcq')
            if seed_wcq and not row.get('wcq'):
                row = dict(row)
                row['wcq'] = seed_wcq
        if row:
            out[team] = row
    return out


def save_team_form(config, team_map, refresh_espn=False):
    token = read_secret(
        config.get('api_token_file', 'static/basedata/football-data.txt'),
        config.get('api_token_env', 'FOOTBALL_DATA_TOKEN'),
    )
    espn_form = load_json(ESPN_CACHE_PATH, {}) if not refresh_espn else {}
    if refresh_espn or len(espn_form) < 40:
        espn_form = fetch_espn_form()
    wc_form = build_team_form_wc(fetch_finished_wc(token), team_map)
    seed_form = load_json(FORM_SEED_PATH, {})
    form = merge_form(wc_form, espn_form, seed_form)
    save_json(FORM_PATH, form)
    print(f'team_form: {len(form)} teams (wc={len(wc_form)}, espn={len(espn_form)})')
    return form
