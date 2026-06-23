"""Match starting lineups: fetch locally (ESPN), serve from JSON on PA."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from briefing.dqd_player_stats import names_loosely_match
from briefing.espn_goals import fetch_espn_summary, find_espn_event_id
from briefing.scorer_match import _name_order_variants, normalize_player_name

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINEUP_PATH = os.path.join(ROOT, 'data', 'briefing', 'match_lineups.json')
NEGATIVE_TTL_MIN = 15


def _load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_lineup_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(LINEUP_PATH), exist_ok=True)
    with open(LINEUP_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_lineup_cache() -> dict:
    return _load_json(LINEUP_PATH, {}) or {}


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _starter_names(starter: dict) -> list[str]:
    names = []
    for field in ('display', 'full', 'short'):
        val = starter.get(field)
        if val:
            names.append(val)
    return names


def _names_equivalent(a: str, b: str) -> bool:
    if not a or not b:
        return False
    na, nb = normalize_player_name(a), normalize_player_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if names_loosely_match(a, b):
        return True
    for variant in _name_order_variants(na):
        if variant == nb:
            return True
    for variant in _name_order_variants(nb):
        if variant == na:
            return True
    return False


def _player_is_starter(player: dict, starters: list[dict]) -> bool:
    name_en = player.get('name_en') or player.get('name') or ''
    for starter in starters:
        for sn in _starter_names(starter):
            if _names_equivalent(name_en, sn):
                return True
    return False


def _extract_starters(summary: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {'home': [], 'away': []}
    for team_block in summary.get('rosters') or []:
        side = team_block.get('homeAway')
        if side not in out:
            continue
        for row in team_block.get('roster') or []:
            if not row.get('starter'):
                continue
            athlete = row.get('athlete') or {}
            out[side].append({
                'display': athlete.get('displayName'),
                'full': athlete.get('fullName'),
                'short': athlete.get('shortName'),
                'jersey': row.get('jersey'),
            })
    return out


def fetch_espn_lineup(fix: dict) -> dict | None:
    """Return lineup block for a fixture, or None if unavailable."""
    home_en = fix.get('home_team_api') or fix.get('home_team')
    away_en = fix.get('away_team_api') or fix.get('away_team')
    event_id = find_espn_event_id(home_en, away_en, fix.get('utc_date'))
    if not event_id:
        return None
    summary = fetch_espn_summary(event_id)
    if not summary:
        return None
    starters = _extract_starters(summary)
    if not starters['home'] and not starters['away']:
        return None
    return {
        'fixture_id': fix.get('fixture_id'),
        'available': True,
        'home': starters['home'],
        'away': starters['away'],
        'espn_event_id': event_id,
        'source': 'espn',
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def _cache_stale(entry: dict | None) -> bool:
    if not entry:
        return True
    if entry.get('available'):
        return False
    ts = _parse_ts(entry.get('updated_at'))
    if not ts:
        return True
    return datetime.now() - ts > timedelta(minutes=NEGATIVE_TTL_MIN)


def resolve_lineup(fix: dict) -> dict | None:
    """Read cached lineup only (safe on PythonAnywhere free tier)."""
    fixture_id = fix.get('fixture_id')
    if fixture_id is None:
        return None
    entry = load_lineup_cache().get(str(fixture_id))
    if entry and entry.get('available'):
        return entry
    return None


def fixtures_for_lineup_backfill(fixtures: list[dict], history_index=None) -> list[dict]:
    """All finished fixtures from history that need lineup cache."""
    from briefing_data import all_report_finished_fixture_ids

    ids = all_report_finished_fixture_ids(history_index)
    by_id = {f['fixture_id']: f for f in fixtures}
    return [by_id[fid] for fid in sorted(ids) if fid in by_id]


def backfill_finished_lineups(fixtures: list[dict], *, force: bool = False) -> dict:
    """Fetch ESPN lineups for every finished match in history."""
    return refresh_match_lineups(fixtures_for_lineup_backfill(fixtures), force=force)


def refresh_match_lineups(target_fixtures: list[dict], *, force: bool = False) -> dict:
    """Fetch lineups from ESPN on the build machine; persist to match_lineups.json."""
    cache = load_lineup_cache()
    stats = {'checked': 0, 'updated': 0, 'available': 0, 'pending': 0}
    seen: set[int] = set()

    for fix in target_fixtures:
        fid = fix.get('fixture_id')
        if fid is None or fid in seen:
            continue
        seen.add(fid)
        stats['checked'] += 1
        key = str(fid)
        entry = cache.get(key)
        if not force and entry and entry.get('available'):
            stats['available'] += 1
            continue
        if not force and not _cache_stale(entry):
            stats['pending'] += 1
            continue

        fresh = fetch_espn_lineup(fix)
        if fresh:
            cache[key] = fresh
            stats['updated'] += 1
            stats['available'] += 1
        else:
            cache[key] = {
                'fixture_id': fid,
                'available': False,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            stats['pending'] += 1

    save_lineup_cache(cache)
    return stats


def annotate_roster_starters(roster: dict, starters: list[dict]) -> dict:
    """Add starter=True to drafted players in the starting XI."""
    if not starters:
        return roster
    out = {}
    for person, raw in roster.items():
        if not raw:
            out[person] = raw
            continue
        players = raw if isinstance(raw, list) else [raw]
        out[person] = [
            {**p, 'starter': _player_is_starter(p, starters)}
            for p in players
        ]
    return out


def annotate_match_rosters(fix: dict, home_roster: dict, away_roster: dict) -> tuple[dict, dict, bool]:
    """Mark starters on both team rosters when cached lineup data exists."""
    lineup = resolve_lineup(fix)
    if not lineup:
        return home_roster, away_roster, False
    home = annotate_roster_starters(home_roster, lineup.get('home') or [])
    away = annotate_roster_starters(away_roster, lineup.get('away') or [])
    return home, away, True


def starter_picks_for_fixture(fix: dict) -> list[int]:
    """Draft pick numbers (# on match page) for players in the starting XI."""
    home_roster = None
    away_roster = None
    try:
        from briefing_data import get_roster_for_team
        home_roster = get_roster_for_team(fix['home_team'])
        away_roster = get_roster_for_team(fix['away_team'])
    except Exception:
        return []
    home, away, ok = annotate_match_rosters(fix, home_roster, away_roster)
    if not ok:
        return []
    picks = []
    for roster in (home, away):
        for players in roster.values():
            if not players:
                continue
            for p in players:
                if p.get('starter') and p.get('pick') is not None:
                    picks.append(int(p['pick']))
    return picks


def enrich_history_starter_picks(fixtures: list[dict]) -> int:
    """Attach starter_picks to finished matches in history_index (for PA upload)."""
    from briefing_data import HISTORY_PATH, load_history_index, match_has_results, save_json

    idx = load_history_index()
    by_id = {f['fixture_id']: f for f in fixtures}
    updated = 0
    for report in (idx.get('reports') or {}).values():
        for m in report.get('matches') or []:
            if not match_has_results(m):
                continue
            fix = by_id.get(m.get('fixture_id'))
            if not fix:
                continue
            picks = starter_picks_for_fixture(fix)
            if picks:
                m['starter_picks'] = picks
                updated += 1
    if updated:
        save_json(HISTORY_PATH, idx)
    return updated
