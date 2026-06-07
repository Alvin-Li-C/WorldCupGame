"""Rebuild our_scorers in history from football-data API (after manual map repair)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.secrets import read_secret
from briefing.shooter_standings import save_shooter_standings
from briefing.standings import save_team_standings
from briefing.time_utils import now_bj
from briefing_data import (
    HISTORY_PATH,
    load_fixtures,
    load_history_index,
    load_json,
    save_json,
    get_selections_for_display,
)
from scripts.build_daily_briefing import (
    api_match_to_report,
    fetch_wc_matches,
    fixture_pair_index,
    load_config,
    load_team_name_map,
)


def rebuild_scorers_from_api():
    config = load_config()
    team_map = load_team_name_map(config)
    fixtures = load_fixtures()
    pair_index = fixture_pair_index(fixtures)
    selections = get_selections_for_display()

    token = read_secret(
        config.get('api_token_file', 'static/basedata/football-data.txt'),
        config.get('api_token_env', 'FOOTBALL_DATA_TOKEN'),
    )
    api_matches = fetch_wc_matches(token, season=2026)
    finished = {m.get('id'): m for m in api_matches if m.get('status') == 'FINISHED'}

    idx = load_history_index()
    reports = idx.get('reports') or {}
    updated = 0
    for date_str, report in reports.items():
        new_matches = []
        for m in report.get('matches') or []:
            if m.get('home_score') is None:
                new_matches.append(m)
                continue
            fix_id = m.get('fixture_id')
            fix = next((f for f in fixtures if f['fixture_id'] == fix_id), None)
            if not fix or not fix.get('api_match_id'):
                new_matches.append(m)
                continue
            api_m = finished.get(fix['api_match_id'])
            if not api_m:
                new_matches.append(m)
                continue
            row = api_match_to_report(api_m, pair_index, team_map, selections)
            if row:
                new_matches.append(row)
                updated += 1
            else:
                new_matches.append(m)
        reports[date_str] = {
            'date': date_str,
            'match_count': len(new_matches),
            'matches': new_matches,
        }

    idx['reports'] = reports
    idx['updated_at'] = now_bj().isoformat(timespec='seconds')
    save_json(HISTORY_PATH, idx)
    save_shooter_standings()
    save_team_standings()
    return {'updated_matches': updated, 'standings': load_json(
        os.path.join(ROOT, 'data', 'briefing', 'standings_shooters.json'),
    )}
