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
from briefing.form_fetch import save_team_form
from briefing.news_fetch import prefilter_for_match
from briefing.odds_fetch import attach_odds_to_matches, merge_odds_into_matches, save_match_odds
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


def build_today_matches(fixtures, date_str, owner_map, config, selections, skip_news=False, prior_matches=None):
    prior_by_id = {
        m['fixture_id']: m for m in (prior_matches or []) if m.get('fixture_id') is not None
    }
    today_fix = sorted(
        fixtures_on_date(fixtures, date_str),
        key=lambda x: x.get('kickoff_beijing', ''),
    )
    overrides = load_json(os.path.join(BRIEFING_DIR, 'news_overrides.json'), {})
    matches = []
    for f in today_fix:
        home, away = f['home_team'], f['away_team']
        picks = [s['name_cn'] for s in selections if s['team_name'] in (home, away)]
        key = f"{f['fixture_id']}"
        if skip_news:
            if key in overrides:
                key_news = overrides[key]
            else:
                key_news = (prior_by_id.get(f['fixture_id']) or {}).get('key_news') or []
        else:
            candidates = prefilter_for_match(
                home,
                away,
                config,
                picks,
                team_hints_en=[f.get('home_team_api'), f.get('away_team_api')],
            )
            if key in overrides:
                key_news = overrides[key]
            else:
                key_news = select_key_news(
                    home,
                    away,
                    candidates,
                    config,
                    picks,
                    team_hints_en=[f.get('home_team_api'), f.get('away_team_api')],
                )
        matches.append({
            'fixture_id': f['fixture_id'],
            'group': f.get('group'),
            'stage': f.get('stage'),
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


def upsert_history_reports(finished_rows):
    """Persist finished matches grouped by played_date_beijing (kickoff calendar day)."""
    idx = load_history_index()
    if 'reports' not in idx:
        idx['reports'] = {}
    by_date = {}
    for row in finished_rows:
        d = row.get('played_date_beijing') or (row.get('kickoff_beijing') or '').split(' ', 1)[0]
        if not d:
            continue
        by_date.setdefault(d, {})[row['fixture_id']] = row
    for d, incoming in by_date.items():
        existing = {
            m['fixture_id']: m
            for m in (idx['reports'].get(d) or {}).get('matches') or []
            if m.get('fixture_id') is not None
        }
        existing.update(incoming)
        matches = sorted(existing.values(), key=lambda m: m.get('kickoff_beijing', ''))
        idx['reports'][d] = {
            'date': d,
            'match_count': len(matches),
            'matches': matches,
        }
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


def build_finished_from_api(api_matches, date_str, fixtures, selections, team_map):
    pair_index = fixture_pair_index(fixtures)
    reports = []
    for m in api_matches_on_beijing_date(api_matches, date_str):
        row = api_match_to_report(m, pair_index, team_map, selections)
        if row:
            reports.append(row)
    return reports


def collect_finished_results(api_matches, date_strings, fixtures, selections, team_map):
    """Dedupe finished API rows across one or more Beijing calendar days."""
    by_id = {}
    for date_str in date_strings:
        for row in build_finished_from_api(api_matches, date_str, fixtures, selections, team_map):
            by_id[row['fixture_id']] = row
    return list(by_id.values())


def merge_finished_into_preview(preview_matches, finished_rows):
    """Attach scores to preview rows when API reports FINISHED on the same fixture."""
    by_id = {r['fixture_id']: r for r in finished_rows}
    merged = []
    for m in preview_matches:
        row = dict(m)
        fr = by_id.get(row.get('fixture_id'))
        if fr:
            row.update({
                'home_score': fr['home_score'],
                'away_score': fr['away_score'],
                'status': 'finished',
                'our_scorers': fr.get('our_scorers') or [],
                'unmatched_scorers': fr.get('unmatched_scorers') or [],
                'played_date_beijing': fr.get('played_date_beijing'),
                'source': fr.get('source', 'football-data'),
            })
            if fr.get('winner_team'):
                row['winner_team'] = fr['winner_team']
            if fr.get('stage'):
                row['stage'] = fr['stage']
        merged.append(row)
    return merged


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


def build_briefing(mock=False, skip_news=False):
    print('build: loading config and fixtures...', flush=True)
    config = load_config()
    fixtures = load_fixtures()

    if not mock:
        try:
            from scripts.enrich_fixture_weather import enrich_all_fixtures
            from briefing.weather_analysis import save_weather_goals_analysis
            print('build: enriching missing fixture weather (Open-Meteo)...', flush=True)
            n = enrich_all_fixtures(force=False, pause=0.2)
            if n:
                print(f'build: weather updated for {n} fixture(s)', flush=True)
            fixtures = load_fixtures()
            save_weather_goals_analysis(fixtures=fixtures)
        except Exception as e:
            print(f'build: weather enrich skipped: {e}', flush=True)

    owner_map = get_owner_map()
    team_map = load_team_name_map(config)
    prior_latest = load_json(LATEST_PATH, {}) if skip_news else {}

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
            today = latest.get('today') or {}
            today['matches'] = merge_odds_into_matches(today.get('matches') or [])
            latest['today'] = today
            save_json(LATEST_PATH, latest)
            return latest

    token = read_secret(
        config.get('api_token_file', 'static/basedata/football-data.txt'),
        config.get('api_token_env', 'FOOTBALL_DATA_TOKEN'),
    )
    print('build: fetching WC matches from football-data...', flush=True)
    api_matches = fetch_wc_matches(token, season=2026)
    # Include briefing_date: early-morning kickoffs (e.g. 03:00 BJ) belong to "today", not calendar yesterday.
    finished_rows = collect_finished_results(
        api_matches,
        [yesterday_date, briefing_date],
        fixtures,
        selections,
        team_map,
    )
    if finished_rows:
        by_day = {}
        for row in finished_rows:
            d = row.get('played_date_beijing') or ''
            by_day[d] = by_day.get(d, 0) + 1
        summary = ', '.join(f'{d} {n}' for d, n in sorted(by_day.items()))
        print(f'build: API finished matches — {summary}', flush=True)
    else:
        print('build: API finished matches — none', flush=True)

    yesterday_matches = build_yesterday_placeholder(fixtures, yesterday_date)

    finished_ids = {r['fixture_id'] for r in finished_rows}
    preview_date, is_next = resolve_preview_date(fixtures, briefing_date, finished_ids, now=now)
    prior_today_matches = (prior_latest.get('today') or {}).get('matches') or []
    if skip_news:
        print(f'build: skip news — refreshing scores; preview {preview_date} reuses cached key_news...', flush=True)
    else:
        print(f'build: fetching news for preview {preview_date}...', flush=True)
    today_matches = build_today_matches(
        fixtures,
        preview_date,
        owner_map,
        config,
        selections,
        skip_news=skip_news,
        prior_matches=prior_today_matches,
    )
    today_matches = merge_finished_into_preview(today_matches, finished_rows)
    print(f'build: {len(today_matches)} preview matches, attaching odds...', flush=True)
    fixtures_by_id = {f['fixture_id']: f for f in fixtures}
    today_matches = attach_odds_to_matches(today_matches, fixtures_by_id, config)
    save_match_odds(today_matches)
    print('build: refreshing team form cache...', flush=True)
    save_team_form(config, team_map)

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
    if finished_rows:
        upsert_history_reports(finished_rows)
    archive = os.path.join(BRIEFING_DIR, f'{briefing_date}.json')
    save_json(archive, briefing)
    save_team_standings()
    save_shooter_standings()

    if not mock:
        try:
            from briefing.lineup_fetch import fixtures_for_lineup_backfill, refresh_match_lineups
            from briefing_data import fixtures_on_date

            preview_date = (briefing.get('today') or {}).get('date') or briefing_date
            lineup_targets = {
                f['fixture_id']: f
                for f in fixtures_on_date(fixtures, preview_date)
                + fixtures_on_date(fixtures, yesterday_date)
                + fixtures_for_lineup_backfill(fixtures)
            }
            if lineup_targets:
                stats = refresh_match_lineups(list(lineup_targets.values()))
                print(
                    'build: lineups — '
                    f"checked {stats['checked']}, "
                    f"new {stats['updated']}, "
                    f"available {stats['available']}, "
                    f"pending {stats['pending']}",
                    flush=True,
                )
        except Exception as e:
            print(f'build: lineup fetch skipped: {e}', flush=True)

        try:
            from briefing.lineup_fetch import enrich_history_starter_picks, enrich_latest_starter_picks
            n = enrich_history_starter_picks(fixtures)
            if n:
                print(f'build: starter_picks embedded in {n} history match(es)', flush=True)
            n2 = enrich_latest_starter_picks(fixtures)
            if n2:
                print(f'build: starter_picks embedded in {n2} preview match(es)', flush=True)
        except Exception as e:
            print(f'build: starter_picks enrich skipped: {e}', flush=True)

    return briefing


def _briefing_upload_payload():
    from briefing.shooter_standings import STANDINGS_PATH as SHOOTER_STANDINGS_PATH
    from briefing.standings import STANDINGS_PATH
    from briefing_data import FIXTURES_PATH, SQUAD_META_PATH, TEAM_FORM_PATH

    payload = {
        'latest': load_json(LATEST_PATH),
        'history_index': load_json(HISTORY_PATH),
        'standings_teams': load_json(STANDINGS_PATH),
        'standings_shooters': load_json(SHOOTER_STANDINGS_PATH),
        'team_squad_meta': load_json(SQUAD_META_PATH, {}),
        'team_form': load_json(TEAM_FORM_PATH, {}),
        'fixtures_2026': load_json(FIXTURES_PATH, {}),
        'weather_goals_analysis': load_json(
            os.path.join(ROOT, 'data', 'briefing', 'weather_goals_analysis.json'), {},
        ),
        'match_lineups': load_json(
            os.path.join(ROOT, 'data', 'briefing', 'match_lineups.json'), {},
        ),
    }
    extras = []
    if payload['team_squad_meta']:
        extras.append(f"squad_meta={len(payload['team_squad_meta'])} teams")
    if payload['team_form']:
        extras.append(f"team_form={len(payload['team_form'])} teams")
    fx = payload['fixtures_2026'].get('fixtures') if isinstance(payload['fixtures_2026'], dict) else None
    if fx:
        extras.append(f"fixtures={len(fx)}")
    lineups = payload.get('match_lineups') or {}
    lineup_ok = sum(1 for v in lineups.values() if isinstance(v, dict) and v.get('available'))
    if lineup_ok:
        extras.append(f"lineups={lineup_ok}")
    if extras:
        print('upload extras: ' + ', '.join(extras), flush=True)
    return payload


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
    print(f'Uploading {len(body)} bytes to {url} ...', flush=True)
    req = urllib.request.Request(
        f'{url}?token={token}',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors='replace')[:2000]
        print(f'Upload failed: HTTP {e.code} {e.reason}', file=sys.stderr)
        if err_body.strip():
            print(err_body, file=sys.stderr)
        print(
            'Hint: if PA returns 500 on all pages, open Web → Error log / Reload on PythonAnywhere.',
            file=sys.stderr,
        )
        sys.exit(1)


def git_push():
    subprocess.run(['git', 'add', 'data/briefing'], cwd=ROOT, check=True)
    subprocess.run(['git', 'commit', '-m', 'chore: update daily briefing JSON'], cwd=ROOT, check=True)
    subprocess.run(['git', 'push'], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mock', action='store_true', help='Refresh timestamps on existing sample JSON')
    parser.add_argument(
        '--skip-news',
        action='store_true',
        help='Skip news search/LLM; refresh match results and standings (reuse cached key_news)',
    )
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

    print('Starting daily briefing build...', flush=True)
    briefing = build_briefing(mock=args.mock, skip_news=args.skip_news)
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
