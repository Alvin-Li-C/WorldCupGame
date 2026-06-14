"""Fetch and parse goal events from ESPN summary API (football-data fallback)."""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from briefing.espn_teams import ESPN_TEAM_CN

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TEAM_MAP_PATH = os.path.join(_ROOT, 'data', 'team_name_map.json')
_alias_cache: dict[int, dict[str, str]] = {}

_SITE = 'https://site.api.espn.com/apis/site/v2/sports/soccer'
_USER_AGENT = 'Mozilla/5.0 (compatible; WorldCupGame/1.0)'
_GOAL_RE = re.compile(
    r'Goal!\s+.+?\.\s+(.+?)\s+\(([^)]+)\)',
    re.IGNORECASE,
)
_MINUTE_RE = re.compile(r"(\d+)'")


def _fetch_json(url: str, retries: int = 3, pause: float = 1.5):
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
            last_err = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 400):
                return None
        time.sleep(pause * (attempt + 1))
    raise RuntimeError(last_err or f'fetch failed: {url}')


def _team_names_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()


def _ascii_fold(name: str) -> str:
    return unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower().strip()


# ESPN scoreboard names that differ from football-data (e.g. Türkiye vs Turkey).
_TEAM_EQUIV_KEYS = {
    'turkiye': 'turkey',
}


def _team_equiv_key(name: str | None) -> str:
    key = _ascii_fold(name or '')
    return _TEAM_EQUIV_KEYS.get(key, key)


def _load_team_map() -> dict:
    try:
        with open(_TEAM_MAP_PATH, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _espn_lookup_aliases(team_map: dict | None = None) -> dict[str, str]:
    """Map football-data / API English names to ESPN scoreboard displayName."""
    tm = team_map if team_map is not None else _load_team_map()
    key = id(tm)
    if key in _alias_cache:
        return _alias_cache[key]
    cn_to_espn = {cn: en for en, cn in ESPN_TEAM_CN.items()}
    aliases: dict[str, str] = {}
    for api_en, cn in tm.items():
        espn_en = cn_to_espn.get(cn)
        if espn_en:
            aliases[api_en] = espn_en
    for espn_en in ESPN_TEAM_CN:
        aliases.setdefault(espn_en, espn_en)
    _alias_cache[key] = aliases
    return aliases


def espn_lookup_name(name: str | None, team_map: dict | None = None) -> str | None:
    """Normalize a team name to ESPN scoreboard displayName."""
    if not name:
        return None
    aliases = _espn_lookup_aliases(team_map)
    if name in aliases:
        return aliases[name]
    folded = _ascii_fold(name)
    for src, dst in aliases.items():
        if _ascii_fold(src) == folded:
            return dst
    return name


def teams_equivalent(a: str | None, b: str | None, team_map: dict | None = None) -> bool:
    if not a or not b:
        return False
    if _team_names_match(a, b):
        return True
    if _team_equiv_key(a) == _team_equiv_key(b):
        return True
    return espn_lookup_name(a, team_map) == espn_lookup_name(b, team_map)


def _espn_date_param(utc_date: str | None) -> str | None:
    if not utc_date or len(utc_date) < 10:
        return None
    return utc_date[:10].replace('-', '')


def _espn_date_candidates(utc_date: str | None) -> list[str]:
    """ESPN scoreboard dates may differ from football-data UTC calendar day."""
    primary = _espn_date_param(utc_date)
    if not primary:
        return []
    try:
        base = datetime.strptime(utc_date[:10], '%Y-%m-%d')
    except ValueError:
        return [primary]
    out = []
    for delta in (0, -1, 1):
        out.append((base + timedelta(days=delta)).strftime('%Y%m%d'))
    return out


def _match_event_on_scoreboard(
    data: dict,
    home_en: str,
    away_en: str,
    team_map: dict | None,
) -> str | None:
    for event in data.get('events') or []:
        comp = (event.get('competitions') or [{}])[0]
        home_name = away_name = None
        for c in comp.get('competitors') or []:
            team = c.get('team') or {}
            name = team.get('displayName') or team.get('name')
            if c.get('homeAway') == 'home':
                home_name = name
            elif c.get('homeAway') == 'away':
                away_name = name
        if teams_equivalent(home_name, home_en, team_map) and teams_equivalent(away_name, away_en, team_map):
            eid = event.get('id')
            return str(eid) if eid is not None else None
    return None


def find_espn_event_id(
    home_en: str,
    away_en: str,
    utc_date: str | None,
    team_map: dict | None = None,
) -> str | None:
    """Resolve ESPN event id from fifa.world scoreboard on match UTC date."""
    for dates in _espn_date_candidates(utc_date):
        url = f'{_SITE}/fifa.world/scoreboard?dates={dates}'
        try:
            data = _fetch_json(url, retries=2, pause=1.0)
        except RuntimeError:
            continue
        if not data:
            continue
        eid = _match_event_on_scoreboard(data, home_en, away_en, team_map)
        if eid:
            return eid
    return None


def fetch_espn_summary(event_id: str | int) -> dict | None:
    url = f'{_SITE}/fifa.world/summary?event={event_id}'
    try:
        return _fetch_json(url, retries=3, pause=1.5)
    except RuntimeError:
        return None


def _parse_minute(play: dict) -> int | None:
    clock = play.get('clock') or {}
    disp = clock.get('displayValue') or ''
    m = _MINUTE_RE.search(disp)
    if m:
        return int(m.group(1))
    val = clock.get('value')
    if val is not None:
        try:
            return int(float(val) // 60)
        except (TypeError, ValueError):
            pass
    return None


def _scorer_from_text(text: str) -> tuple[str | None, str | None]:
    m = _GOAL_RE.search(text or '')
    if not m:
        return None, None
    return m.group(1).strip(), m.group(2).strip()


def _goal_type(play: dict) -> str | None:
    ptype = ((play.get('type') or {}).get('type') or '').lower()
    if ptype == 'own-goal' or 'own-goal' in ptype:
        return 'OWN'
    if ptype in ('penalty-goal', 'penalty') or 'penalty' in ptype:
        return 'PENALTY'
    if ptype == 'goal' or ptype.startswith('goal'):
        return 'REGULAR'
    return None


def _team_cn(team_en: str | None, home_en: str, away_en: str, home_cn: str | None, away_cn: str | None,
             team_map: dict, api_team_to_cn) -> str | None:
    cn = api_team_to_cn(team_en, team_map)
    if cn:
        return cn
    if team_en and teams_equivalent(team_en, home_en, team_map):
        return home_cn
    if team_en and teams_equivalent(team_en, away_en, team_map):
        return away_cn
    if team_en:
        return ESPN_TEAM_CN.get(team_en)
    return None


def parse_espn_goal_events(
    summary: dict,
    team_map: dict,
    api_team_to_cn,
    home_en: str,
    away_en: str,
) -> list[dict]:
    """Return goal events in the same shape as extract_scoring_events."""
    home_cn = (
        api_team_to_cn(home_en, team_map)
        or ESPN_TEAM_CN.get(espn_lookup_name(home_en, team_map) or '')
        or ESPN_TEAM_CN.get(home_en)
    )
    away_cn = (
        api_team_to_cn(away_en, team_map)
        or ESPN_TEAM_CN.get(espn_lookup_name(away_en, team_map) or '')
        or ESPN_TEAM_CN.get(away_en)
    )
    events = []
    seen_ids: set[str] = set()

    for play in summary.get('keyEvents') or []:
        if play.get('shootout'):
            continue
        gtype = _goal_type(play)
        if not gtype:
            continue
        pid = play.get('id')
        if pid is not None:
            key = str(pid)
            if key in seen_ids:
                continue
            seen_ids.add(key)

        team_en = (play.get('team') or {}).get('displayName')
        scorer_en = None
        scorer_api_id = None
        parts = play.get('participants') or []
        if parts:
            athlete = parts[0].get('athlete') or {}
            scorer_en = athlete.get('displayName')
            scorer_api_id = athlete.get('id')
        if not scorer_en:
            scorer_en, parsed_team = _scorer_from_text(play.get('text') or '')
            if not team_en and parsed_team:
                team_en = parsed_team
        if not scorer_en:
            continue

        team_cn = _team_cn(team_en, home_en, away_en, home_cn, away_cn, team_map, api_team_to_cn)
        events.append({
            'scorer_en': scorer_en,
            'scorer_api_id': scorer_api_id,
            'team_en': team_en,
            'team_cn': team_cn,
            'type': gtype,
            'minute': _parse_minute(play),
        })
    return events


def fetch_espn_scoring_events(
    home_en: str,
    away_en: str,
    utc_date: str | None,
    team_map: dict,
    api_team_to_cn,
    event_id: str | int | None = None,
) -> list[dict]:
    """Look up ESPN event and return parsed goal events (empty list on failure)."""
    eid = event_id or find_espn_event_id(home_en, away_en, utc_date, team_map)
    if not eid:
        return []
    summary = fetch_espn_summary(eid)
    if not summary:
        return []
    return parse_espn_goal_events(summary, team_map, api_team_to_cn, home_en, away_en)
