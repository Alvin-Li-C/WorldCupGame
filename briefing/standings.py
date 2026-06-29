"""Team standings for draft pool owners (小组赛 + 晋级奖励 + 淘汰赛)."""
from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from briefing.match_score import resolve_winner_from_report
from briefing_data import (
    BRIEFING_DIR,
    collect_finished_match_map,
    get_owner_map,
    load_briefing,
    load_fixtures,
    load_history_index,
    load_json,
    save_json,
)

BJ = timezone(timedelta(hours=8))
STANDINGS_PATH = os.path.join(BRIEFING_DIR, 'standings_teams.json')

GROUP_WIN, GROUP_DRAW = 3, 1
GROUP_BONUS_ADVANCE = 1
KNOCKOUT_WIN = 3
THIRD_PLACE_WIN = 1  # 三四名决赛胜者（季军）；败者（第四名）不加分
FINAL_WIN = 4

KNOCKOUT_ADVANCE_STAGES = frozenset({'last_32', 'round_16', 'quarter', 'semi'})
BEST_THIRD_PLACES = 8


@dataclass
class TeamStanding:
    team: str
    group: str | None = None
    owner: str | None = None
    w: int = 0
    d: int = 0
    l: int = 0
    gf: int = 0
    ga: int = 0
    group_pts: int = 0
    bonus_pts: int = 0
    bonus_reason: str = ''
    knockout_pts: int = 0
    played: int = 0

    @property
    def gd(self) -> int:
        return self.gf - self.ga

    @property
    def total_pts(self) -> int:
        return self.group_pts + self.bonus_pts + self.knockout_pts


def _participant_names(owner_map):
    from models import get_db

    db = get_db()
    rows = db.execute('SELECT name FROM participants ORDER BY draft_order').fetchall()
    db.close()
    names = [r['name'] for r in rows]
    if names:
        return names
    return sorted({o for o in owner_map.values() if o})


def collect_finished_matches(history=None, latest=None):
    """Deduplicate finished matches from history and latest briefing blocks."""
    return collect_finished_match_map(history, latest)


def _fixture_index(fixtures):
    return {f['fixture_id']: f for f in fixtures}


def _owned(owner_map, team):
    owner = owner_map.get(team)
    return owner if owner else None


def _rank_key(team_stat: TeamStanding):
    return (-team_stat.group_pts, -team_stat.gd, -team_stat.gf, team_stat.team)


def _group_fixtures(fixtures, group):
    return [
        f for f in fixtures
        if f.get('stage') == 'group' and f.get('group') == group
    ]


def _group_complete(group_fixtures, results_by_id):
    if len(group_fixtures) < 6:
        return False
    return all(f['fixture_id'] in results_by_id for f in group_fixtures)


def _all_groups_complete(fixtures, results_by_id):
    groups = {f['group'] for f in fixtures if f.get('stage') == 'group' and f.get('group')}
    return bool(groups) and all(
        _group_complete(_group_fixtures(fixtures, g), results_by_id)
        for g in groups
    )


def _apply_group_match(team_stats, owner_map, home, away, hs, aw):
    """Update group standings for every team (ranking); owner only set when drafted."""
    for team, scored, conceded, outcome in (
        (home, hs, aw, 'w' if hs > aw else 'd' if hs == aw else 'l'),
        (away, aw, hs, 'w' if aw > hs else 'd' if hs == aw else 'l'),
    ):
        st = team_stats[team]
        st.team = team
        owner = _owned(owner_map, team)
        if owner:
            st.owner = owner
        st.played += 1
        st.gf += scored
        st.ga += conceded
        if outcome == 'w':
            st.w += 1
            st.group_pts += GROUP_WIN
        elif outcome == 'd':
            st.d += 1
            st.group_pts += GROUP_DRAW
        else:
            st.l += 1


def _apply_knockout_bonus(team_stats, owner_map, stage, winner):
    owner = _owned(owner_map, winner)
    if not owner:
        return
    st = team_stats[winner]
    st.owner = owner
    if stage in KNOCKOUT_ADVANCE_STAGES:
        st.knockout_pts += KNOCKOUT_WIN
    elif stage == 'third_place':
        st.knockout_pts += THIRD_PLACE_WIN
    elif stage == 'final':
        st.knockout_pts += FINAL_WIN


def _apply_knockout_match_record(team_stats, owner_map, home, away, hs, aw, winner):
    """Count knockout W/L and played; does not add group-stage points."""
    for team, scored, conceded, outcome in (
        (home, hs, aw, 'w' if winner == home else 'l'),
        (away, aw, hs, 'w' if winner == away else 'l'),
    ):
        st = team_stats[team]
        st.team = team
        owner = _owned(owner_map, team)
        if owner:
            st.owner = owner
        st.played += 1
        st.gf += scored
        st.ga += conceded
        if outcome == 'w':
            st.w += 1
        else:
            st.l += 1


def compute_team_standings(history=None, latest=None, fixtures=None, owner_map=None):
    owner_map = owner_map or get_owner_map()
    fixtures = fixtures if fixtures is not None else load_fixtures()
    fix_idx = _fixture_index(fixtures)
    results_by_id = collect_finished_matches(history, latest)

    team_to_group = {}
    for f in fixtures:
        if f.get('stage') == 'group' and f.get('group'):
            for t in (f['home_team'], f['away_team']):
                team_to_group[t] = f['group']

    team_stats: dict[str, TeamStanding] = defaultdict(lambda: TeamStanding(team=''))

    for team in owner_map:
        team_stats[team].team = team
        team_stats[team].group = team_to_group.get(team)

    for fid, m in results_by_id.items():
        fix = fix_idx.get(fid)
        if not fix or fix.get('stage') != 'group':
            continue
        home, away = m['home_team'], m['away_team']
        hs, aw = m['home_score'], m['away_score']
        group = fix.get('group')
        for t in (home, away):
            team_stats[t].team = t
            team_stats[t].group = group
        _apply_group_match(team_stats, owner_map, home, away, hs, aw)

    groups = sorted({f['group'] for f in fixtures if f.get('stage') == 'group' and f.get('group')})
    third_place_candidates: list[TeamStanding] = []
    all_groups_done = _all_groups_complete(fixtures, results_by_id)

    for group in groups:
        g_fix = _group_fixtures(fixtures, group)
        if not _group_complete(g_fix, results_by_id):
            continue
        group_teams = sorted(
            {f['home_team'] for f in g_fix} | {f['away_team'] for f in g_fix},
        )
        ranked = sorted(
            (team_stats[t] for t in group_teams),
            key=_rank_key,
        )
        if len(ranked) < len(group_teams):
            continue
        for place, st in enumerate(ranked[:2], start=1):
            if st.owner:
                st.bonus_pts += GROUP_BONUS_ADVANCE
                st.bonus_reason = f'小组第{place}出线'
        third = ranked[2]
        third.group = group
        third_place_candidates.append(third)

    if all_groups_done:
        advancing_thirds = set()
        if third_place_candidates:
            ordered_thirds = sorted(third_place_candidates, key=_rank_key)
            for st in ordered_thirds[:BEST_THIRD_PLACES]:
                advancing_thirds.add(st.team)

        for st in third_place_candidates:
            if st.team in advancing_thirds and st.owner:
                st.bonus_pts += GROUP_BONUS_ADVANCE
                st.bonus_reason = '小组第3出线'

    for fid, m in results_by_id.items():
        fix = fix_idx.get(fid)
        stage = (fix or {}).get('stage') or m.get('stage')
        if stage == 'group' or not stage:
            continue
        winner = resolve_winner_from_report(
            m, m['home_team'], m['away_team'], m['home_score'], m['away_score'],
        )
        if not winner:
            continue
        group = (fix or {}).get('group')
        if group:
            team_stats[winner].group = group
        _apply_knockout_match_record(
            team_stats, owner_map, m['home_team'], m['away_team'], m['home_score'], m['away_score'], winner,
        )
        _apply_knockout_bonus(team_stats, owner_map, stage, winner)

    participants_out = []
    for name in _participant_names(owner_map):
        owned = [st for st in team_stats.values() if st.owner == name]
        points = sum(st.total_pts for st in owned)
        participants_out.append({
            'participant': name,
            'points': points,
            'wins': sum(st.w for st in owned),
            'draws': sum(st.d for st in owned),
            'losses': sum(st.l for st in owned),
            'played': sum(st.played for st in owned),
            'group_pts': sum(st.group_pts for st in owned),
            'bonus_pts': sum(st.bonus_pts for st in owned),
            'knockout_pts': sum(st.knockout_pts for st in owned),
            'teams': sorted(
                [
                    {
                        'team': st.team,
                        'group': st.group or '—',
                        'w': st.w,
                        'd': st.d,
                        'l': st.l,
                        'group_pts': st.group_pts,
                        'bonus_pts': st.bonus_pts,
                        'bonus_reason': st.bonus_reason,
                        'knockout_pts': st.knockout_pts,
                        'total_pts': st.total_pts,
                    }
                    for st in owned
                    if st.played or st.bonus_pts or st.knockout_pts
                ],
                key=lambda x: (-x['total_pts'], x['team']),
            ),
        })

    participants_out.sort(key=lambda x: (-x['points'], x['participant']))
    for i, row in enumerate(participants_out, 1):
        row['rank'] = i

    now = datetime.now(BJ).isoformat(timespec='seconds')
    has_results = bool(results_by_id)
    return {
        'generated_at': now,
        'empty': not has_results,
        'rules': {
            'group_win': GROUP_WIN,
            'group_draw': GROUP_DRAW,
            'group_bonus_advance': GROUP_BONUS_ADVANCE,
            'knockout_win': KNOCKOUT_WIN,
            'third_place_win': THIRD_PLACE_WIN,
            'third_place_note': '三四名决赛胜者（季军）+1；败者（第四名）+0',
            'final_win': FINAL_WIN,
            'knockout_note': '淘汰赛只看晋级结果；加时或点球大战不影响加分，晋级方按场次规则得分',
            'record_note': '胜/平/负/场次含小组赛与淘汰赛',
        },
        'participants': participants_out,
    }


def save_team_standings(data=None):
    data = data if data is not None else compute_team_standings()
    save_json(STANDINGS_PATH, data)
    return data


def load_team_standings():
    try:
        return compute_team_standings()
    except Exception:
        cached = load_json(STANDINGS_PATH)
        if cached:
            return cached
        raise
