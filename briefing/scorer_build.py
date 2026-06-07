"""Build our_scorers and unmatched_scorers for a match report."""
from briefing.goal_events import event_points, extract_scoring_events
from briefing.scorer_match import REASON_LABELS, match_scorer_to_selection


def build_match_scorers(api_match, home_cn, away_cn, team_map, selections, api_team_to_cn, match_meta=None):
    """
    Return dict with our_scorers[], unmatched_scorers[].
    match_meta: optional {fixture_id, kickoff_beijing, home_team, away_team}
    """
    meta = match_meta or {}
    events = extract_scoring_events(api_match, team_map, api_team_to_cn)
    stats = {}
    unmatched = []

    for ev in events:
        sel, reason = match_scorer_to_selection(ev, selections)
        g_delta, og_delta = event_points(ev)
        would_points = g_delta + og_delta * 2

        if not sel:
            if reason == 'not_drafted':
                continue
            unmatched.append({
                'fixture_id': meta.get('fixture_id'),
                'kickoff_beijing': meta.get('kickoff_beijing'),
                'home_team': meta.get('home_team', home_cn),
                'away_team': meta.get('away_team', away_cn),
                'scorer_en': ev.get('scorer_en'),
                'scorer_api_id': ev.get('scorer_api_id'),
                'team_en': ev.get('team_en'),
                'team_cn': ev.get('team_cn'),
                'type': ev.get('type'),
                'minute': ev.get('minute'),
                'would_points': would_points,
                'reason': reason,
                'reason_label': REASON_LABELS.get(reason, reason),
            })
            continue

        pid = sel['player_id']
        if pid not in stats:
            stats[pid] = {'sel': sel, 'goals': 0, 'own_goals': 0}
        stats[pid]['goals'] += g_delta
        stats[pid]['own_goals'] += og_delta

    our_scorers = []
    for st in stats.values():
        sel = st['sel']
        goals = st['goals']
        ogs = st['own_goals']
        points = goals + ogs * 2
        our_scorers.append({
            'player_id': sel['player_id'],
            'participant': sel['participant'],
            'player_name_cn': sel.get('name_cn') or sel.get('name'),
            'player_name_en': sel.get('name'),
            'jersey_number': sel.get('jersey_number'),
            'goals': goals,
            'own_goals': ogs,
            'points': points,
            'goal_count': goals,
            'display': (
                f'+{goals}' if goals and not ogs
                else (f'乌龙+{ogs * 2}' if ogs and not goals else (
                    f'+{goals} 乌龙+{ogs * 2}' if goals and ogs else '+0'
                ))
            ),
            'top20': sel.get('pick_number', 99) <= 20,
        })
    our_scorers.sort(key=lambda x: (-x['points'], x['player_name_cn']))
    return {'our_scorers': our_scorers, 'unmatched_scorers': unmatched}
