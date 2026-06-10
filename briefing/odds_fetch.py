"""Fetch h2h odds from BetExplorer (free, no API key) and attach to briefing matches."""
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ODDS_PATH = os.path.join(ROOT, 'data', 'briefing', 'match_odds.json')
SEED_PATH = os.path.join(ROOT, 'data', 'briefing', 'match_odds_seed.json')

TEAM_ALIASES = {
    'south korea': 'korea republic',
    'czech republic': 'czechia',
    'usa': 'united states',
    'curacao': 'curaçao',
}


def implied_prob(home, draw, away):
    ih, id_, ia = 1 / home, 1 / draw, 1 / away
    total = ih + id_ + ia
    return {
        'home_pct': round(ih / total * 100, 1),
        'draw_pct': round(id_ / total * 100, 1),
        'away_pct': round(ia / total * 100, 1),
    }


def norm_team(name):
    if not name:
        return ''
    s = unicodedata.normalize('NFKD', name)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z0-9 ]', '', s.lower()).strip()
    return TEAM_ALIASES.get(s, s)


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def odds_row(home, draw, away, source='betexplorer'):
    return {
        'home': round(home, 2),
        'draw': round(draw, 2),
        'away': round(away, 2),
        'implied_prob': implied_prob(home, draw, away),
        'updated_at': datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M'),
        'source': source,
    }


class _BetExplorerMatchParser(HTMLParser):
    """Parse table-main__matchInfo rows for home/away and 1X2 odds."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self._in_li = False
        self._in_home = False
        self._in_away = False
        self._in_odd = False
        self._cur = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get('class', '')
        if tag == 'li' and 'table-main__matchInfo' in cls:
            self._in_li = True
            self._cur = {'home': '', 'away': '', 'odds': []}
        elif self._in_li and 'participantHome' in cls:
            self._in_home = True
            self._text = []
        elif self._in_li and 'participantAway' in cls:
            self._in_away = True
            self._text = []
        elif self._in_li and 'table-main__odd' in cls:
            self._in_odd = True
            self._text = []

    def handle_endtag(self, tag):
        if tag == 'p' and self._in_home:
            self._cur['home'] = ''.join(self._text).strip()
            self._in_home = False
        elif tag == 'p' and self._in_away:
            self._cur['away'] = ''.join(self._text).strip()
            self._in_away = False
        elif tag in ('div', 'span') and self._in_odd:
            raw = ''.join(self._text).strip()
            if re.fullmatch(r'\d+\.\d+', raw):
                self._cur['odds'].append(float(raw))
            self._in_odd = False
        elif tag == 'li' and self._in_li:
            self._in_li = False
            if self._cur and len(self._cur.get('odds', [])) >= 3:
                self.rows.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._in_home or self._in_away or self._in_odd:
            self._text.append(data)


def _is_youth_or_women(home, away):
    junk = (' W', ' U17', ' U19', ' U20', ' U21', ' U23', ' Women')
    blob = f'{home} {away}'
    return any(j in blob for j in junk)


def parse_betexplorer_html(html):
    parser = _BetExplorerMatchParser()
    parser.feed(html)
    index = {}
    for row in parser.rows:
        home, away = row['home'], row['away']
        if not home or not away or _is_youth_or_women(home, away):
            continue
        odds = row['odds'][:3]
        if len(odds) < 3:
            continue
        key = (norm_team(home), norm_team(away))
        index[key] = odds_row(odds[0], odds[1], odds[2])
        index[(norm_team(away), norm_team(home))] = odds_row(odds[2], odds[1], odds[0])
    return index


def fetch_betexplorer_index(config):
    odds_cfg = config.get('odds') or {}
    url = odds_cfg.get(
        'fixtures_url',
        'https://www.betexplorer.com/football/world/world-cup-2026/fixtures/',
    )
    timeout = int(odds_cfg.get('timeout', 30))
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; WorldCupGameBriefing/1.0)',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', 'replace')
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f'betexplorer odds fetch failed: {e}')
        return {}
    index = parse_betexplorer_html(html)
    if not index:
        print('betexplorer: no 1X2 rows parsed (page may be JS-only or empty)')
    else:
        print(f'betexplorer: parsed {len(index) // 2} match rows')
    return index


def match_fixture_to_odds(fix, index):
    home = norm_team(fix.get('home_team_api') or fix.get('home_team'))
    away = norm_team(fix.get('away_team_api') or fix.get('away_team'))
    return index.get((home, away))


def attach_odds_to_matches(matches, fixtures_by_id, config):
    index = fetch_betexplorer_index(config)
    seed = load_json(SEED_PATH, {})
    seed_map = seed.get('fixtures') or seed if isinstance(seed, dict) else {}
    for m in matches:
        fid = m.get('fixture_id')
        fix = fixtures_by_id.get(fid)
        if not fix:
            continue
        odds = match_fixture_to_odds(fix, index) if index else None
        if not odds:
            odds = seed_map.get(str(fid)) or seed_map.get(fid)
        if odds:
            m['odds'] = odds
    return matches


def save_match_odds(matches):
    by_id = {}
    for m in matches:
        if m.get('odds') and m.get('fixture_id') is not None:
            by_id[str(m['fixture_id'])] = m['odds']
    if not by_id:
        return by_id
    payload = {
        'updated_at': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
        'source': 'betexplorer',
        'fixtures': by_id,
    }
    save_json(ODDS_PATH, payload)
    return by_id


def load_match_odds():
    data = load_json(ODDS_PATH, {})
    return data.get('fixtures') or {}


def load_match_odds_seed():
    data = load_json(SEED_PATH, {})
    return data.get('fixtures') or {}


def resolve_odds_for_fixture(fixture_id, inline_odds=None):
    if inline_odds:
        return inline_odds
    key = str(fixture_id)
    cached = load_match_odds().get(key)
    if cached:
        return cached
    return load_match_odds_seed().get(key)


def merge_odds_into_matches(matches):
    """Attach odds from cache/seed when match objects lack them."""
    cache = load_match_odds()
    seed = load_match_odds_seed()
    for m in matches:
        if m.get('odds'):
            continue
        fid = str(m.get('fixture_id', ''))
        m['odds'] = cache.get(fid) or seed.get(fid)
    return matches
