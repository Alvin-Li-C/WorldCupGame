#!/usr/bin/env python3
"""Inject Koki Ogawa (小川航基) goal for 庆爷 into shooter standings demo."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.shooter_standings import save_shooter_standings
from briefing_data import HISTORY_PATH, load_json, save_json
from models import get_db

OGAWA_ID = 562
QINGYE_PARTICIPANT_ID = 2
FIXTURE_ID = 19  # 德国 vs 日本


def ensure_ogawa_drafted():
    db = get_db()
    exists = db.execute('SELECT 1 FROM selections WHERE player_id=?', (OGAWA_ID,)).fetchone()
    if not exists:
        nxt = db.execute('SELECT COALESCE(MAX(pick_number), 0) + 1 FROM selections').fetchone()[0]
        db.execute(
            'INSERT INTO selections (round_number, pick_number, participant_id, player_id) VALUES (?, ?, ?, ?)',
            (3, nxt, QINGYE_PARTICIPANT_ID, OGAWA_ID),
        )
        db.commit()
        print('Added Koki Ogawa to 庆爷 selections')
    row = db.execute('''
        SELECT p.name AS participant, pl.name, pl.name_cn, pl.jersey_number, t.name AS team_name,
               s.pick_number
        FROM selections s
        JOIN participants p ON p.id = s.participant_id
        JOIN players pl ON pl.id = s.player_id
        JOIN teams t ON t.id = pl.team_id
        WHERE pl.id = ?
    ''', (OGAWA_ID,)).fetchone()
    db.close()
    return dict(row)


def scorer_row(sel):
    top20 = (sel.get('pick_number') or 99) <= 20
    return {
        'player_id': OGAWA_ID,
        'participant': sel['participant'],
        'player_name_cn': sel['name_cn'] or sel['name'],
        'player_name_en': sel['name'],
        'jersey_number': sel['jersey_number'],
        'goals': 1,
        'own_goals': 0,
        'points': 1,
        'goal_count': 1,
        'display': '+1',
        'top20': top20,
    }


def inject_goal(sel):
    idx = load_json(HISTORY_PATH)
    row_data = scorer_row(sel)
    for report in idx.get('reports', {}).values():
        for m in report.get('matches') or []:
            if m.get('fixture_id') != FIXTURE_ID:
                continue
            scorers = list(m.get('our_scorers') or [])
            if not any(s.get('player_id') == OGAWA_ID for s in scorers):
                scorers.append(row_data)
            m['our_scorers'] = scorers
            m['unmatched_scorers'] = m.get('unmatched_scorers') or []
            print(f"Injected goal: {sel['name_cn'] or sel['name']} in {m['home_team']} vs {m['away_team']}")
    save_json(HISTORY_PATH, idx)
    data = save_shooter_standings()
    top = [p for p in data['players'] if p['points'] > 0]
    print('Standings scorers:', [(p['participant'], p['name'], p['points']) for p in top])


if __name__ == '__main__':
    inject_goal(ensure_ogawa_drafted())
