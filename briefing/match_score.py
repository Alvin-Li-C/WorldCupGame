"""Resolve match winners from API or stored reports (incl. penalties)."""


def resolve_winner_from_api(api_match, home_cn, away_cn):
    """Winner by API result; overtime/penalties do not affect who advances."""
    score = api_match.get('score') or {}
    winner = score.get('winner')
    if winner == 'HOME_TEAM':
        return home_cn
    if winner == 'AWAY_TEAM':
        return away_cn
    pen = score.get('penalties') or {}
    ph, pa = pen.get('home'), pen.get('away')
    if ph is not None and pa is not None and ph != pa:
        return home_cn if ph > pa else away_cn
    ft = score.get('fullTime') or {}
    hs, aw = ft.get('home'), ft.get('away')
    if hs is not None and aw is not None:
        if hs > aw:
            return home_cn
        if aw > hs:
            return away_cn
    return None


def resolve_winner_from_report(match, home, away, home_score, away_score):
    """Prefer stored winner_team (knockout); fall back to 90-minute scores."""
    stored = match.get('winner_team')
    if stored in (home, away):
        return stored
    if home_score > away_score:
        return home
    if away_score > home_score:
        return away
    return None
