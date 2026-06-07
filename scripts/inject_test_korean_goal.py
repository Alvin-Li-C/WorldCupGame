#!/usr/bin/env python3
"""Inject Son Heung-min goal into history for shooter standings demo."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.shooter_standings import save_shooter_standings
from briefing_data import HISTORY_PATH, load_json, save_json
from models import get_db

SON_ID = 102


def ensure_son_drafted():
    db = get_db()
    exists = db.execute('SELECT 1 FROM selections WHERE player_id=?', (SON_ID,)).fetchone()
    if not exists:
        db.execute(
            'INSERT INTO selections (round_number, pick_number, participant_id, player_id) VALUES (?, ?, ?, ?)',
            (3, 1, 3, SON_ID),
        )
        db.commit()
        print('Added Heung-Min Son to 李总 selections')
    else:
        print('Son already drafted')
    row = db.execute('''
        SELECT p.name AS participant, pl.name, pl.name_cn, pl.jersey_number, t.name AS team_name
        FROM selections s
        JOIN participants p ON p.id = s.participant_id
        JOIN players pl ON pl.id = s.player_id
        JOIN teams t ON t.id = pl.team_id
        WHERE pl.id = ?
    ''', (SON_ID,)).fetchone()
    db.close()
    return dict(row)


def inject_goal(sel):
    idx = load_json(HISTORY_PATH)
    for report in idx.get('reports', {}).values():
        for m in report.get('matches') or []:
            if m.get('fixture_id') != 2:
                continue
            m['our_scorers'] = [{
                'player_id': SON_ID,
                'participant': sel['participant'],
                'player_name_cn': sel['name_cn'] or sel['name'],
                'player_name_en': sel['name'],
                'jersey_number': sel['jersey_number'],
                'goals': 1,
                'own_goals': 0,
                'points': 1,
                'goal_count': 1,
                'display': '+1',
                'top20': False,
            }]
            m['unmatched_scorers'] = []
            print(f"Injected goal: {sel['name']} in {m['home_team']} vs {m['away_team']}")
    save_json(HISTORY_PATH, idx)
    data = save_shooter_standings()
    top = [p for p in data['players'] if p['points'] > 0]
    print('Standings scorers:', [(p['name'], p['points']) for p in top])


if __name__ == '__main__':
    sel = ensure_son_drafted()
    inject_goal(sel)
