"""Daily participant rank series for standings chart (WC start → refresh date)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from briefing_data import load_briefing, load_history_index, today_bj_str

BJ = timezone(timedelta(hours=8))
WC_START = '2026-06-12'


def _matches_by_date(history: dict, latest: dict | None = None) -> dict[str, list]:
    by_date: dict[str, list] = {}
    seen: set[int] = set()

    def add_match(m: dict, fallback_date: str) -> None:
        fid = m.get('fixture_id')
        if fid in seen or m.get('home_score') is None:
            return
        seen.add(fid)
        d = m.get('played_date_beijing') or fallback_date
        by_date.setdefault(d, []).append(m)

    for date in sorted((history.get('reports') or {}).keys()):
        for m in (history['reports'][date].get('matches') or []):
            add_match(m, date)

    if latest:
        y = latest.get('yesterday') or {}
        ydate = y.get('date')
        if ydate:
            for m in y.get('matches') or []:
                add_match(m, ydate)

    return by_date


def compute_daily_series(end_date: str | None = None, colors: dict | None = None) -> dict:
    """Build rank/goals time series for the five fantasy participants."""
    history = load_history_index()
    latest = load_briefing()
    end_date = end_date or today_bj_str()
    by_date = _matches_by_date(history, latest)

    all_dates = sorted(d for d in by_date if WC_START <= d <= end_date)
    if not all_dates:
        return {
            'generated_at': datetime.now(BJ).isoformat(timespec='seconds'),
            'start_date': WC_START,
            'end_date': end_date,
            'dates': [],
            'date_labels': [],
            'participants': [],
            'daily': [],
            'series': {},
        }

    all_names: set[str] = set()
    for matches in by_date.values():
        for m in matches:
            for row in m.get('our_scorers') or []:
                if row.get('participant'):
                    all_names.add(row['participant'])

    cumulative: dict[str, dict] = {
        p: {'goals': 0, 'own_goals': 0, 'points': 0} for p in all_names
    }
    daily_rows = []

    for d in all_dates:
        for m in by_date[d]:
            for row in m.get('our_scorers') or []:
                p = row.get('participant')
                if not p:
                    continue
                goals = row.get('goals', row.get('goal_count', 0)) or 0
                ogs = row.get('own_goals', 0) or 0
                pts = row.get('points')
                if pts is None:
                    pts = goals + ogs * 2
                if p not in cumulative:
                    cumulative[p] = {'goals': 0, 'own_goals': 0, 'points': 0}
                cumulative[p]['goals'] += goals
                cumulative[p]['own_goals'] += ogs
                cumulative[p]['points'] += pts

        ranked = sorted(
            cumulative.items(),
            key=lambda x: (-x[1]['points'], -x[1]['goals'], x[0]),
        )
        ranks = {name: i + 1 for i, (name, _) in enumerate(ranked)}
        daily_rows.append({
            'date': d,
            'label': d[5:].replace('-', '/'),
            'standings': [
                {
                    'participant': name,
                    'rank': ranks[name],
                    'goals': stats['goals'],
                    'own_goals': stats['own_goals'],
                    'points': stats['points'],
                }
                for name, stats in ranked
            ],
        })

    participants = [
        name for name, _ in sorted(
            cumulative.items(),
            key=lambda x: (-x[1]['points'], -x[1]['goals'], x[0]),
        )
    ]

    palette = colors or {}
    series = {}
    for p in participants:
        series[p] = {
            'color': palette.get(p, '#888'),
            'ranks': [],
            'goals': [],
            'points': [],
        }
        for row in daily_rows:
            st = next(s for s in row['standings'] if s['participant'] == p)
            series[p]['ranks'].append(st['rank'])
            series[p]['goals'].append(st['goals'])
            series[p]['points'].append(st['points'])

    return {
        'generated_at': datetime.now(BJ).isoformat(timespec='seconds'),
        'start_date': WC_START,
        'end_date': end_date,
        'dates': [r['date'] for r in daily_rows],
        'date_labels': [r['label'] for r in daily_rows],
        'participants': participants,
        'daily': daily_rows,
        'series': series,
    }
