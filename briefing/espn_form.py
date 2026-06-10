"""Parse ESPN national-team results pages into last-5 form."""
import re
import time
import urllib.error
import urllib.request
from datetime import date

from bs4 import BeautifulSoup

_MONTH = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}
_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'


def _parse_row_date(date_txt, ref_year=2026):
    """Parse 'Thu, Jun 4' -> ISO date."""
    m = re.search(r'([A-Za-z]{3}),\s*([A-Za-z]{3})\s+(\d{1,2})', date_txt or '')
    if not m:
        return ''
    mon = _MONTH.get(m.group(2).lower()[:3])
    if not mon:
        return ''
    day = int(m.group(3))
    year = ref_year
    if mon > 8:
        year = ref_year - 1
    return date(year, mon, day).isoformat()


def _parse_score(score_txt):
    m = re.match(r'(\d+)\s*-\s*(\d+)', (score_txt or '').strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


_NAME_ALIASES = {
    'korea republic': ('south korea', 'korea'),
    'czech republic': ('czechia', 'czech republic'),
    'united states': ('united states', 'usa'),
    'ivory coast': ("cote d'ivoire", 'ivory coast'),
    'dr congo': ('congo dr', 'dr congo', 'congo'),
    'cape verde': ('cape verde',),
    'bosnia-herzegovina': ('bosnia', 'bosnia and herzegovina'),
}


def _team_names(team_name):
    base = team_name.lower().replace('turkey', 'turkiye')
    names = {base, base.replace('-', ' ')}
    names.update(_NAME_ALIASES.get(base.replace('-', ' '), ()))
    return names


def _matches_team(label, names):
    lab = label.lower()
    return any(n in lab or lab in n for n in names)


def parse_espn_results_html(html, team_name, cutoff_date='2026-06-11'):
    """Return finished matches newest-first: {date, char, gf, ga}."""
    soup = BeautifulSoup(html, 'html.parser')
    names = _team_names(team_name)
    rows = []
    for tr in soup.find_all('tr'):
        tds = [td.get_text(' ', strip=True) for td in tr.find_all('td')]
        if len(tds) < 5:
            continue
        if tds[4] != 'FT':
            continue
        score = _parse_score(tds[2])
        if not score:
            continue
        home, away = tds[1], tds[3]
        hs, aw = score
        iso = _parse_row_date(tds[0])
        if iso and iso > cutoff_date:
            continue
        if _matches_team(home, names):
            ch = 'W' if hs > aw else ('L' if hs < aw else 'D')
            gf, ga = hs, aw
        elif _matches_team(away, names):
            ch = 'W' if aw > hs else ('L' if aw < hs else 'D')
            gf, ga = aw, hs
        else:
            continue
        rows.append({'date': iso or tds[0], 'char': ch, 'gf': gf, 'ga': ga})
    rows.sort(key=lambda r: r['date'], reverse=True)
    return rows


def rows_to_form(rows, n=5):
    last = list(reversed(rows[:n]))
    if not last:
        return None
    return {
        'last5': ''.join(r['char'] for r in last),
        'goals_for': sum(r['gf'] for r in last),
        'goals_against': sum(r['ga'] for r in last),
        'updated_at': last[-1].get('date'),
        'source': 'espn',
    }


def fetch_team_results(espn_id, slug, retries=5):
    url = f'https://www.espn.com/soccer/team/results/_/id/{espn_id}/{slug}'
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={'User-Agent': _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read()
            if len(raw) > 5000:
                return raw.decode('utf-8', 'replace')
            last_err = f'short response ({len(raw)} bytes, status {getattr(resp, "status", "?")})'
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = str(e)
        time.sleep(4 * (attempt + 1))
    raise RuntimeError(last_err or 'empty ESPN response')
