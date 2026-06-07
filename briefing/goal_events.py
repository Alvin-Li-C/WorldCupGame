"""Extract scoring events from football-data API matches."""

GOAL_TYPES = frozenset({'REGULAR', 'PENALTY', 'OWN'})


def extract_scoring_events(api_match, team_map, api_team_to_cn):
    """Return goal events from match; ignores penalty-shootout lists."""
    home_en = api_match.get('homeTeam', {}).get('name')
    away_en = api_match.get('awayTeam', {}).get('name')
    home_cn = api_team_to_cn(home_en, team_map)
    away_cn = api_team_to_cn(away_en, team_map)
    events = []
    for g in api_match.get('goals') or []:
        gtype = (g.get('type') or 'REGULAR').upper()
        if gtype not in GOAL_TYPES:
            continue
        scorer = g.get('scorer') or {}
        team = g.get('team') or {}
        scorer_en = scorer.get('name')
        team_en = team.get('name')
        if not scorer_en:
            continue
        team_cn = api_team_to_cn(team_en, team_map)
        if not team_cn:
            if team_en == home_en:
                team_cn = home_cn
            elif team_en == away_en:
                team_cn = away_cn
        events.append({
            'scorer_en': scorer_en,
            'scorer_api_id': scorer.get('id'),
            'team_en': team_en,
            'team_cn': team_cn,
            'type': gtype,
            'minute': g.get('minute'),
        })
    return events


def event_points(event: dict) -> tuple[int, int]:
    """Return (goals_delta, own_goals_delta) for one event."""
    if event.get('type') == 'OWN':
        return 0, 1
    return 1, 0
