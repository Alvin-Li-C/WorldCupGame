#!/usr/bin/env python3
"""Remove demo match results from briefing history (team + shooter standings)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.standings import save_team_standings
from briefing.shooter_standings import save_shooter_standings
from briefing_data import HISTORY_PATH, LATEST_PATH, load_json, save_json


def clean_history_results():
    idx = load_json(HISTORY_PATH, {'reports': {}})
    removed = 0
    for report in idx.get('reports', {}).values():
        before = list(report.get('matches') or [])
        report['matches'] = [
            m for m in before
            if m.get('home_score') is None or m.get('away_score') is None
        ]
        removed += len(before) - len(report['matches'])
        report['match_count'] = len(report['matches'])
    save_json(HISTORY_PATH, idx)
    return removed


def clean_latest_yesterday():
    latest = load_json(LATEST_PATH)
    if not latest:
        return 0
    yesterday = latest.get('yesterday') or {}
    before = list(yesterday.get('matches') or [])
    yesterday['matches'] = [
        m for m in before
        if m.get('home_score') is None or m.get('away_score') is None
    ]
    removed = len(before) - len(yesterday['matches'])
    yesterday['match_count'] = len(yesterday['matches'])
    latest['yesterday'] = yesterday
    save_json(LATEST_PATH, latest)
    return removed


def main():
    h = clean_history_results()
    y = clean_latest_yesterday()
    teams = save_team_standings()
    shooters = save_shooter_standings()
    print(f'Removed {h} finished match(es) from history, {y} from latest.yesterday')
    print('Team standings empty:', teams.get('empty'))
    print('Shooter standings empty:', shooters.get('empty'))


if __name__ == '__main__':
    main()
