#!/usr/bin/env python3
"""Remove demo scorer injections (Son / Ogawa) from history and optional DB selections."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.shooter_standings import save_shooter_standings
from briefing_data import HISTORY_PATH, load_json, save_json
from models import get_db

TEST_PLAYER_IDS = {102, 562}  # Heung-Min Son, Koki Ogawa


def clean_history():
    idx = load_json(HISTORY_PATH)
    removed = 0
    for report in idx.get('reports', {}).values():
        for m in report.get('matches') or []:
            before = list(m.get('our_scorers') or [])
            m['our_scorers'] = [
                s for s in before
                if s.get('player_id') not in TEST_PLAYER_IDS
                and s.get('player_name_en') not in ('Heung-Min Son', 'Koki Ogawa')
                and (s.get('player_name_cn') or '') not in ('孙兴慜', '小川航基')
            ]
            removed += len(before) - len(m['our_scorers'])
    save_json(HISTORY_PATH, idx)
    return removed


def clean_selections():
    db = get_db()
    cur = db.execute(
        f'DELETE FROM selections WHERE player_id IN ({",".join("?" * len(TEST_PLAYER_IDS))})',
        tuple(TEST_PLAYER_IDS),
    )
    db.commit()
    n = cur.rowcount
    db.close()
    return n


def main():
    h = clean_history()
    s = clean_selections()
    data = save_shooter_standings()
    scorers = [p for p in data['players'] if p['points'] > 0]
    print(f'Removed {h} history scorer row(s), {s} test selection(s)')
    print('Players with points:', [(p['name'], p['points']) for p in scorers])


if __name__ == '__main__':
    main()
