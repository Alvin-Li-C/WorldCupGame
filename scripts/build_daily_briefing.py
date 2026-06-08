#!/usr/bin/env python3
"""Build daily briefing JSON on PC. Does not write to draft tables."""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.llm_news import select_key_news
from briefing.validate import upload_summary, validate_briefing_payload
from briefing_data import report_has_results
from briefing.match_score import resolve_winner_from_api
from briefing.scorer_build import build_match_scorers
from briefing.shooter_standings import save_shooter_standings
from briefing.standings import save_team_standings
from briefing.news_fetch import prefilter_for_match
from briefing.secrets import read_secret
from briefing.time_utils import (
    beijing_date_from_utc,
    beijing_datetime_str,
    now_bj,
    today_bj_str,
    yesterday_bj_str,
)
from briefing_data import (
    BRIEFING_DIR,
    HISTORY_PATH,
    LATEST_PATH,
    fixtures_on_date,
    get_owner_map,
    get_selections_for_display,
    load_fixtures,
    load_history_index,
    load_json,
    matches_on_beijing_date,
    open_db_readonly,
    resolve_preview_date,
    save_json,
)

TEAM_MAP_PATH = os.path.join(ROOT, 'data', 'team_name_map.json')
WC_API = 'https://api.football-data.org/v4/competitions/WC/matches'


def load_config():
    return load_json(os.path.join(ROOT, 'data', 'scraper_config.json'), {})


def load_team_name_map(config):
    path = config.get('team_name_map_file', 'data/team_name_map.json')
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    base = load_json(path, {})
    base.update(config.get('team_name_map') or {})
    return base


def api_team_to_cn(name, team_map):
    if not name:
        return None
    return team_map.get(name)


def fixture_pair_index(fixtures):
    idx = {}
    for f in fixtures:
        key = (f['home_team'], f['away_team'])
        idx[key] = f
        idx[(f['away_team'], f['home_team'])] = f
    return idx


def attach_owners(matches, owner_map):
    for m in matches:
        m['home_owner'] = owner_map.get(m['home_team']) or 'NA'
        m['away_owner'] = owner_map.get(m['away_team']) or 'NA'
    return matches


def build_today_matches(fixtures, date_str, owner_map, config, selections):
    today_fix = sorted(
        fixtures_on_date(fixtures, date_str),
        key=lambda x: x.get('kickoff_beijing', ''),
    )
    matches = []
    for f in today_fix:
        home, away = f['home_team'], f['away_team']
        picks = [s['name_cn'] for s in selections if s['team_name'] in (home, away)]
        candidates = prefilter_for_match(
            home,
            away,
            config,
            picks,
            team_hints_en=[f.get('home_team_api'), f.get('away_team_api')],
        )
        overrides = load_json(os.path.join(BRIEFING_DIR, 'news_overrides.json'), {})
        key = f"{f['fixture_id']}"
        if key in overrides:
            key_news = overrides[key]
        else:
            key_news = select_key_news(home, away, candidates, config, picks)
        matches.append({
            'fixture_id': f['fixture_id'],
            'group': f.get('group'),
            'matchday': f.get('matchday'),
            'home_team': home,
            'away_team': away,
            'kickoff_beijing': f['kickoff_beijing'],
            'status': 'scheduled',
            'home_owner': owner_map.get(home) or 'NA',
            'away_owner': owner_map.get(away) or 'NA',
            'key_news': key_news,
        })
    return matches_on_beijing_date(matches, date_str)


def _finished_matches(matches):
    return [
        m for m in (matches or [])
        if m.get('home_score') is not None and m.get('away_score') is not None
    ]


def upsert_history(yesterday_block):
    """Only persist days with at least one finished match."""
    idx = load_history_index()
    if 'reports' not in idx:
        idx['reports'] = {}
    d = yesterday_block['date']
    finished = _finished_matches(yesterday_block.get('matches'))
    if finished:
        idx['reports'][d] = {
            'date': d,
            'match_count': len(finished),
            'matches': finished,
        }
    elif d in idx['reports']:
        del idx['reports'][d]
    idx['dates'] = sorted(
        [day for day, rep in idx['reports'].items() if report_has_results(rep)],
        reverse=True,
    )
    idx['updated_at'] = now_bj().isoformat(timespec='seconds')
    save_json(HISTORY_PATH, idx)


def fetch_wc_matches(token, season=2026, status=None):
    """Fetch WC matches via competition endpoint (not legacy /matches date filter)."""
    if not token:
        return []
    url = f'{WC_API}?season={season}'
    if status:
        url += f'&status={status}'
    req = urllib.request.Request(
        url,
        headers={'X-Auth-Token': token, 'X-Unfold-Goals': 'true'},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data.get('matches', [])
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        print(f'football-data fetch failed: {e}')
        return []


def api_matches_on_beijing_date(api_matches, date_str):
    """赛果日按北京时间日历日筛选（非 UTC 日）。"""
    out = []
    for m in api_matches:
        if m.get('status') != 'FINISHED':
            continue
        bj_date = beijing_date_from_utc(m.get('utcDate'))
        if bj_date == date_str:
            out.append(m)
    return out


def resolve_fixture(api_match, pair_index, team_map):
    home_cn = api_team_to_cn(api_match['homeTeam'].get('name'), team_map)
    away_cn = api_team_to_cn(api_match['awayTeam'].get('name'), team_map)
    if not home_cn or not away_cn:
        return None, home_cn, away_cn
    fix = pair_index.get((home_cn, away_cn))
    return fix, home_cn, away_cn


def api_match_to_report(api_match, pair_index, team_map, selections):
    fix, home_cn, away_cn = resolve_fixture(api_match, pair_index, team_map)
    if not fix:
        return None
    ft = (api_match.get('score') or {}).get('fullTime') or {}
    hs, aw = ft.get('home'), ft.get('away')
    if hs is None or aw is None:
        return None
    meta = {
        'fixture_id': fix['fixture_id'],
        'kickoff_beijing': beijing_datetime_str(api_match.get('utcDate')) or fix.get('kickoff_beijing'),
        'home_team': home_cn,
        'away_team': away_cn,
    }
    scorer_block = build_match_scorers(
        api_match, home_cn, away_cn, team_map, selections, api_team_to_cn, match_meta=meta,
    )
    row = {
        'fixture_id': fix['fixture_id'],
        'home_team': home_cn,
        'away_team': away_cn,
        'home_score': hs,
        'away_score': aw,
        'source': 'football-data',
        'stadium_photo': fix.get('stadium_photo', 'azteca.jpg'),
        'played_date_beijing': beijing_date_from_utc(api_match.get('utcDate')),
        'kickoff_beijing': meta['kickoff_beijing'],
        'our_scorers': scorer_block['our_scorers'],
        'unmatched_scorers': scorer_block['unmatched_scorers'],
    }
    winner = resolve_winner_from_api(api_match, home_cn, away_cn)
    if winner:
        row['winner_team'] = winner
    stage = fix.get('stage')
    if stage and stage != 'group':
        row['stage'] = stage
    return row


def build_yesterday_from_api(api_matches, date_str, fixtures, selections, team_map):
    pair_index = fixture_pair_index(fixtures)
    reports = []
    for m in api_matches_on_beijing_date(api_matches, date_str):
        row = api_match_to_report(m, pair_index, team_map, selections)
        if row:
            reports.append(row)
    return reports


def build_yesterday_placeholder(fixtures, date_str):
    rows = []
    for f in fixtures_on_date(fixtures, date_str):
        rows.append({
            'fixture_id': f['fixture_id'],
            'home_team': f['home_team'],
            'away_team': f['away_team'],
            'home_score': None,
            'away_score': None,
            'stadium_photo': f.get('stadium_photo', 'azteca.jpg'),
            'our_scorers': [],
            'unmatched_scorers': [],
        })
    return rows


def build_briefing(mock=False):
    config = load_config()
    fixtures = load_fixtures()
    owner_map = get_owner_map()
    team_map = load_team_name_map(config)

    try:
        conn = open_db_readonly()
        selections = get_selections_for_display(conn)
        conn.close()
    except Exception:
        selections = []

    now = now_bj()
    briefing_date = today_bj_str()
    yesterday_date = yesterday_bj_str()

    if mock:
        from briefing_data import enrich_today_preview

        latest = load_json(LATEST_PATH, {})
        if latest:
            latest['generated_at'] = now.isoformat(timespec='seconds')
            latest['briefing_date'] = briefing_date
            latest['timezone'] = 'Asia/Shanghai'
            latest = enrich_today_preview(latest, reference_date=briefing_date)
            save_json(LATEST_PATH, latest)
            return latest

    token = read_secret(
        config.get('api_token_file', 'static/basedata/football-data.txt'),
        config.get('api_token_env', 'FOOTBALL_DATA_TOKEN'),
    )
    api_matches = fetch_wc_matches(token, season=2026)
    yesterday_matches = build_yesterday_from_api(
        api_matches, yesterday_date, fixtures, selections, team_map,
    )
    if not yesterday_matches:
        yesterday_matches = build_yesterday_placeholder(fixtures, yesterday_date)

    preview_date, is_next = resolve_preview_date(fixtures, briefing_date)
    today_matches = build_today_matches(fixtures, preview_date, owner_map, config, selections)

    briefing = {
        'generated_at': now.isoformat(timespec='seconds'),
        'timezone': 'Asia/Shanghai',
        'briefing_date': briefing_date,
        'yesterday': {'date': yesterday_date, 'matches': yesterday_matches},
        'today': {
            'date': preview_date,
            'is_next_matchday': is_next,
            'match_count': len(today_matches),
            'matches': today_matches,
        },
    }
    save_json(LATEST_PATH, briefing)
    if _finished_matches(yesterday_matches):
        upsert_history(briefing['yesterday'])
    archive = os.path.join(BRIEFING_DIR, f'{briefing_date}.json')
    save_json(archive, briefing)
    save_team_standings()
    save_shooter_standings()
    return briefing


def _briefing_upload_payload():
    from briefing.shooter_standings import STANDINGS_PATH as SHOOTER_STANDINGS_PATH
    from briefing.standings import STANDINGS_PATH

    return {
        'latest': load_json(LATEST_PATH),
        'history_index': load_json(HISTORY_PATH),
        'standings_teams': load_json(STANDINGS_PATH),
        'standings_shooters': load_json(SHOOTER_STANDINGS_PATH),
    }


def upload_briefing(config, dry_run=False):
    payload = _briefing_upload_payload()
    print(upload_summary(payload))
    ok, errors = validate_briefing_payload(payload)
    if not ok:
        print('Upload rejected — briefing data validation failed:')
        for err in errors:
            print(f'  - {err}')
        sys.exit(1)
    if dry_run:
        print('Dry run OK — no data sent to PythonAnywhere')
        return
    url = config.get('pythonanywhere_url', '').rstrip('/') + '/api/import-briefing'
    token = read_secret('', config.get('import_token_env', 'IMPORT_BRIEFING_TOKEN'))
    if not token:
        print('IMPORT_BRIEFING_TOKEN not set; skip upload')
        return
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f'{url}?token={token}',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(resp.read().decode())


def git_push():
    subprocess.run(['git', 'add', 'data/briefing'], cwd=ROOT, check=True)
    subprocess.run(['git', 'commit', '-m', 'chore: update daily briefing JSON'], cwd=ROOT, check=True)
    subprocess.run(['git', 'push'], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mock', action='store_true', help='Refresh timestamps on existing sample JSON')
    parser.add_argument('--upload', action='store_true', help='POST to PythonAnywhere import endpoint')
    parser.add_argument('--dry-run', action='store_true', help='Validate upload payload without POST')
    parser.add_argument('--push', action='store_true', help='git commit/push briefing JSON (requires user Approve)')
    args = parser.parse_args()

    if args.dry_run and not args.upload:
        payload = _briefing_upload_payload()
        print(upload_summary(payload))
        ok, errors = validate_briefing_payload(payload)
        if not ok:
            for err in errors:
                print(f'  - {err}')
            sys.exit(1)
        print('Dry run OK')
        return

    briefing = build_briefing(mock=args.mock)
    y = briefing.get('yesterday', {})
    t = briefing.get('today', {})
    print(
        f"Briefing built: {briefing.get('briefing_date')} (BJ) — "
        f"yesterday {y.get('date')} {len(y.get('matches', []))} matches, "
        f"preview {t.get('date')} {len(t.get('matches', []))} matches"
        f"{' (next matchday)' if t.get('is_next_matchday') else ''}"
    )

    if args.upload:
        upload_briefing(load_config(), dry_run=args.dry_run)
    if args.push:
        git_push()


if __name__ == '__main__':
    main()
