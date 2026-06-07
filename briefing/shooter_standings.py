"""Shooter standings aggregation from briefing history JSON."""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

from briefing_data import (
    BRIEFING_DIR,
    get_selections_for_display,
    load_briefing,
    load_history_index,
    load_json,
    save_json,
)
from models import get_db

BJ = timezone(timedelta(hours=8))
STANDINGS_PATH = os.path.join(BRIEFING_DIR, 'standings_shooters.json')

REASON_LABELS = {
    'not_drafted': '非选秀球员',
    'no_name_match': '英文名未匹配',
    'ambiguous': '同队多名候选',
    'manual_map_not_drafted': '映射球员未选秀',
}


def _participant_names():
    db = get_db()
    rows = db.execute('SELECT name FROM participants ORDER BY draft_order').fetchall()
    db.close()
    return [r['name'] for r in rows]


def _iter_history_matches(history=None, latest=None):
    history = history if history is not None else load_history_index()
    latest = latest if latest is not None else load_briefing()
    seen = set()
    for report in (history.get('reports') or {}).values():
        for m in report.get('matches') or []:
            fid = m.get('fixture_id')
            if fid in seen:
                continue
            if m.get('home_score') is None:
                continue
            seen.add(fid)
            yield m
    for m in (latest.get('yesterday') or {}).get('matches') or [] if latest else []:
        fid = m.get('fixture_id')
        if fid in seen or m.get('home_score') is None:
            continue
        seen.add(fid)
        yield m


def _legacy_resolve_player_id(row, selections):
    """Backward compat for history rows without player_id."""
    if row.get('player_id') is not None:
        return row['player_id']
    cn = row.get('player_name_cn') or ''
    en = row.get('player_name_en') or ''
    part = row.get('participant')
    for s in selections:
        if part and s.get('participant') != part:
            continue
        if cn and s.get('name_cn') == cn:
            return s['player_id']
        if en and s.get('name') == en:
            return s['player_id']
    return None


def _accumulate_scorer_row(agg, row, selections=None):
    pid = row.get('player_id')
    if pid is None and selections:
        pid = _legacy_resolve_player_id(row, selections)
    if pid is None:
        return
    goals = row.get('goals', row.get('goal_count', 0)) or 0
    ogs = row.get('own_goals', 0) or 0
    points = row.get('points')
    if points is None:
        points = goals + ogs * 2
    if pid not in agg:
        agg[pid] = {
            'player_id': pid,
            'participant': row.get('participant'),
            'player_name_cn': row.get('player_name_cn') or row.get('player_name_en', ''),
            'player_name_en': row.get('player_name_en', ''),
            'team': None,
            'pick': row.get('pick_number'),
            'goals': 0,
            'own_goals': 0,
            'points': 0,
            'top20': row.get('top20', False),
        }
    agg[pid]['goals'] += goals
    agg[pid]['own_goals'] += ogs
    agg[pid]['points'] += points


def compute_shooter_standings(history=None, latest=None, selections=None):
    selections = selections if selections is not None else get_selections_for_display()
    sel_by_id = {s['player_id']: s for s in selections}

    player_agg = {}
    unmatched_all = []
    unmatched_keys = set()

    for m in _iter_history_matches(history, latest):
        for row in m.get('our_scorers') or []:
            _accumulate_scorer_row(player_agg, row, selections)
        for u in m.get('unmatched_scorers') or []:
            if u.get('reason') == 'not_drafted':
                continue
            key = (
                u.get('fixture_id'),
                u.get('minute'),
                u.get('scorer_en'),
                u.get('type'),
            )
            if key in unmatched_keys:
                continue
            unmatched_keys.add(key)
            unmatched_all.append(u)

    players_out = []
    for pid, sel in sel_by_id.items():
        base = player_agg.get(pid, {})
        goals = base.get('goals', 0)
        ogs = base.get('own_goals', 0)
        points = base.get('points', goals + ogs * 2)
        players_out.append({
            'player_id': pid,
            'participant': sel['participant'],
            'name': sel.get('name_cn') or sel.get('name'),
            'name_en': sel.get('name'),
            'team': sel['team_name'],
            'pick': sel.get('pick_number'),
            'goals': goals,
            'own_goals': ogs,
            'points': points,
            'top20': sel.get('pick_number', 99) <= 20,
        })

    players_out.sort(key=lambda x: (-x['points'], -x['goals'], x['pick']))
    for i, p in enumerate(players_out, 1):
        p['rank'] = i
    has_scoring = any(p['points'] > 0 for p in players_out)

    part_names = _participant_names() or sorted({s['participant'] for s in selections})
    participants_out = []
    for name in part_names:
        owned = [p for p in players_out if p['participant'] == name]
        participants_out.append({
            'participant': name,
            'points': sum(p['points'] for p in owned),
            'goals': sum(p['goals'] for p in owned),
            'own_goals': sum(p['own_goals'] for p in owned),
        })
    participants_out.sort(key=lambda x: (-x['points'], x['participant']))

    now = datetime.now(BJ).isoformat(timespec='seconds')
    return {
        'generated_at': now,
        'empty': not has_scoring,
        'rules': {
            'goal': 1,
            'own_goal': 2,
            'penalty_shootout': 0,
            'note': '90分钟与加时点球按进球+1；点球大战不计',
        },
        'participants': participants_out,
        'players': players_out,
        'unmatched_count': len(unmatched_all),
        'unmatched': unmatched_all,
    }


def save_shooter_standings(data=None):
    data = data if data is not None else compute_shooter_standings()
    save_json(STANDINGS_PATH, data)
    return data


def load_shooter_standings():
    return compute_shooter_standings()
