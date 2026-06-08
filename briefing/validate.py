"""Validate briefing JSON before upload/import to production."""
from __future__ import annotations

from briefing_data import list_report_dates, load_fixtures, match_has_results, report_has_results

ALLOWED_SOURCE = 'football-data'
TEST_PLAYER_IDS = frozenset({102, 562})  # Son, Ogawa demo injections
TEST_PLAYER_NAMES = frozenset({'孙兴慜', '小川航基', 'Heung-Min Son', 'Koki Ogawa'})


def _fixture_pairs():
    pairs = set()
    for f in load_fixtures():
        pairs.add((f['home_team'], f['away_team']))
    return pairs


def _match_errors(match: dict, fixture_pairs: set) -> list[str]:
    errs = []
    if not match_has_results(match):
        return errs
    fid = match.get('fixture_id')
    home, away = match.get('home_team'), match.get('away_team')
    if (home, away) not in fixture_pairs:
        errs.append(f'fixture {fid}: teams {home} vs {away} not in fixtures_2026.json')
    if match.get('source') != ALLOWED_SOURCE:
        errs.append(
            f'fixture {fid}: missing source={ALLOWED_SOURCE!r} '
            f'(test or manual result?)'
        )
    for s in match.get('our_scorers') or []:
        if s.get('player_id') in TEST_PLAYER_IDS:
            errs.append(f'fixture {fid}: test player_id {s.get("player_id")}')
        name_cn = s.get('player_name_cn') or ''
        name_en = s.get('player_name_en') or s.get('name') or ''
        if name_cn in TEST_PLAYER_NAMES or name_en in TEST_PLAYER_NAMES:
            errs.append(f'fixture {fid}: test scorer {name_cn or name_en}')
    return errs


def validate_history_index(history_index: dict | None) -> list[str]:
    if not history_index:
        return []
    errors = []
    fixture_pairs = _fixture_pairs()
    for date, report in (history_index.get('reports') or {}).items():
        finished = [m for m in (report.get('matches') or []) if match_has_results(m)]
        if not finished:
            if report.get('matches'):
                errors.append(f'{date}: report has matches but none finished (stale index entry)')
            continue
        for m in finished:
            errors.extend(_match_errors(m, fixture_pairs))
    stale_dates = set(history_index.get('dates') or []) - set(list_report_dates(history_index))
    for d in sorted(stale_dates):
        errors.append(f'dates list includes {d} with no finished matches')
    return errors


def validate_briefing_payload(payload: dict) -> tuple[bool, list[str]]:
    errors = []
    if 'history_index' in payload:
        errors.extend(validate_history_index(payload['history_index']))
    latest = payload.get('latest') or {}
    for m in (latest.get('yesterday') or {}).get('matches') or []:
        if match_has_results(m):
            errors.append('latest.yesterday contains finished scores (should only be in history_index)')
    return (len(errors) == 0, errors)


def upload_summary(payload: dict) -> str:
    hist = payload.get('history_index') or {}
    dates = list_report_dates(hist)
    lines = [f'Report dates with results: {len(dates)}']
    for d in dates:
        report = hist['reports'][d]
        n = sum(1 for m in report.get('matches', []) if match_has_results(m))
        lines.append(f'  {d}: {n} finished match(es)')
    if not dates:
        lines.append('  (none — safe empty state)')
    return '\n'.join(lines)
