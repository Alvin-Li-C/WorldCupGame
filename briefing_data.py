"""Read-only briefing data for Flask and build scripts."""
import json
import os
import sqlite3

from briefing.time_utils import fixture_beijing_date, today_bj_str, yesterday_bj_str
from game_logic import global_pick_number, is_top20_pick
from models import DB_PATH, get_db

ROOT = os.path.dirname(os.path.abspath(__file__))
BRIEFING_DIR = os.path.join(ROOT, 'data', 'briefing')
LATEST_PATH = os.path.join(BRIEFING_DIR, 'latest.json')
HISTORY_PATH = os.path.join(BRIEFING_DIR, 'history_index.json')
FIXTURES_PATH = os.path.join(ROOT, 'data', 'fixtures_2026.json')
SQUAD_META_PATH = os.path.join(ROOT, 'data', 'team_squad_meta.json')
TEAM_FORM_PATH = os.path.join(BRIEFING_DIR, 'team_form.json')

CATEGORY_LABELS = {
    'tactics': '战术',
    'discord': '不和',
    'form': '状态',
    'lineup': '阵容',
    'injury': '伤病',
    'suspension': '停赛',
    'other': '其他',
}


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_briefing():
    return load_json(LATEST_PATH)


def load_history_index():
    return load_json(HISTORY_PATH, {'updated_at': None, 'dates': [], 'reports': {}})


def match_has_results(match):
    return match.get('home_score') is not None and match.get('away_score') is not None


def report_has_results(report):
    if not report:
        return False
    return any(match_has_results(m) for m in (report.get('matches') or []))


def list_report_dates(history_index=None):
    idx = history_index if history_index is not None else load_history_index()
    dates = []
    for d, report in (idx.get('reports') or {}).items():
        if report_has_results(report):
            dates.append(d)
    return sorted(dates, reverse=True)


def get_report_for_date(date):
    idx = load_history_index()
    report = idx.get('reports', {}).get(date)
    if not report_has_results(report):
        return None
    return report


def load_fixtures():
    data = load_json(FIXTURES_PATH, {'fixtures': []})
    return data.get('fixtures', [])


def fixtures_on_date(fixtures, date_str):
    return [f for f in fixtures if fixture_beijing_date(f) == date_str]


def beijing_date_label(iso_date):
    """'2026-06-11' -> '6月11日'."""
    if not iso_date:
        return '—'
    parts = iso_date.split('-')
    if len(parts) != 3:
        return iso_date
    return f'{int(parts[1])}月{int(parts[2])}日'


def kickoff_beijing_label(kickoff):
    """'2026-06-11 09:00' -> '6月11日 09:00'."""
    if not kickoff or ' ' not in kickoff:
        return kickoff or ''
    date_part, time_part = kickoff.split(' ', 1)
    return f'{beijing_date_label(date_part)} {time_part}'


def matches_on_beijing_date(matches, date_str):
    """Keep only matches whose kickoff_beijing falls on date_str (Asia/Shanghai)."""
    return [
        m for m in matches
        if (m.get('kickoff_beijing') or '').startswith(date_str)
    ]


def fixture_dates_sorted(fixtures):
    return sorted({fixture_beijing_date(f) for f in fixtures if fixture_beijing_date(f)})


def finished_fixture_ids_for_date(
    date_str,
    history_index=None,
    extra_matches=None,
):
    """Fixture ids with final scores on a Beijing calendar day."""
    ids = set()
    idx = history_index if history_index is not None else load_history_index()
    report = (idx.get('reports') or {}).get(date_str) or {}
    for m in report.get('matches') or []:
        if match_has_results(m):
            ids.add(m['fixture_id'])
    for m in extra_matches or []:
        kickoff = m.get('kickoff_beijing') or ''
        if not kickoff.startswith(date_str):
            continue
        if match_has_results(m) or m.get('status') == 'finished':
            fid = m.get('fixture_id')
            if fid is not None:
                ids.add(fid)
    return ids


def all_fixtures_finished_on_date(fixtures, date_str, finished_fixture_ids):
    day = fixtures_on_date(fixtures, date_str)
    if not day:
        return False
    expected = {f['fixture_id'] for f in day}
    return expected.issubset(set(finished_fixture_ids or ()))


def resolve_preview_date(fixtures, briefing_date, finished_fixture_ids=None):
    """Return (preview_date, is_next_matchday) for 今日预告."""
    finished_fixture_ids = set(finished_fixture_ids or ())
    if fixtures_on_date(fixtures, briefing_date):
        if not all_fixtures_finished_on_date(fixtures, briefing_date, finished_fixture_ids):
            return briefing_date, False
    for d in fixture_dates_sorted(fixtures):
        if d > briefing_date:
            return d, True
    return briefing_date, False


def build_preview_match_skeleton(fixture, owner_map):
    return {
        'fixture_id': fixture['fixture_id'],
        'group': fixture.get('group'),
        'matchday': fixture.get('matchday'),
        'home_team': fixture['home_team'],
        'away_team': fixture['away_team'],
        'kickoff_beijing': fixture['kickoff_beijing'],
        'status': 'scheduled',
        'home_owner': owner_map.get(fixture['home_team']) or 'NA',
        'away_owner': owner_map.get(fixture['away_team']) or 'NA',
        'key_news': [],
    }


def enrich_today_preview(latest, reference_date=None):
    """Fill next matchday when today block is empty or stale.

    reference_date: Beijing calendar day for preview resolution. Flask passes
    today_bj_str() so stale JSON still shows the correct next matchday.
    """
    if not latest:
        return latest
    fixtures = load_fixtures()
    briefing_date = reference_date or latest.get('briefing_date') or today_bj_str()
    today_block = latest.get('today') or {}
    finished_ids = finished_fixture_ids_for_date(
        briefing_date,
        extra_matches=today_block.get('matches') or [],
    )
    preview_date, is_next = resolve_preview_date(fixtures, briefing_date, finished_ids)
    today = dict(latest.get('today') or {})
    owner_map = get_owner_map()
    overrides = load_json(os.path.join(BRIEFING_DIR, 'news_overrides.json'), {})
    existing_by_id = {
        m['fixture_id']: m
        for m in matches_on_beijing_date(today.get('matches') or [], preview_date)
    }
    new_matches = []
    for f in sorted(fixtures_on_date(fixtures, preview_date), key=lambda x: x.get('kickoff_beijing', '')):
        skeleton = build_preview_match_skeleton(f, owner_map)
        existing = existing_by_id.get(f['fixture_id'])
        m = dict(skeleton)
        if existing:
            keep = (
                'key_news', 'status', 'odds',
                'home_score', 'away_score', 'our_scorers', 'unmatched_scorers',
                'winner_team', 'played_date_beijing', 'source', 'stage',
            )
            m.update({k: v for k, v in existing.items() if k in keep and v is not None})
        if not m.get('key_news'):
            override = overrides.get(str(f['fixture_id']))
            if override:
                m['key_news'] = override
        new_matches.append(m)
    latest = dict(latest)
    latest['briefing_date'] = briefing_date
    latest['today'] = {
        'date': preview_date,
        'is_next_matchday': is_next,
        'match_count': len(new_matches),
        'matches': matches_on_beijing_date(new_matches, preview_date),
    }
    return latest


def load_briefing_enriched():
    """Load latest.json with 无赛日 → 下一比赛日 preview applied."""
    return enrich_today_preview(load_briefing() or {}, reference_date=today_bj_str())


def get_owner_map():
    """team_name -> participant name. teamInfo.txt is the source of truth."""
    try:
        from seed_data import load_team_ownership
        ownership = load_team_ownership()
        return {team: owner for owner, teams in ownership.items() for team in teams}
    except (FileNotFoundError, ValueError):
        pass
    db = get_db()
    rows = db.execute('''
        SELECT t.name AS team_name, p.name AS owner
        FROM team_ownership o
        JOIN teams t ON t.id = o.team_id
        JOIN participants p ON p.id = o.participant_id
    ''').fetchall()
    db.close()
    return {r['team_name']: r['owner'] for r in rows}


def owner_display(team_name, owner_map=None):
    if owner_map is None:
        owner_map = get_owner_map()
    return owner_map.get(team_name) or 'NA'


def get_selections_roster():
    """5 participants -> selected player info or null."""
    db = get_db()
    parts = db.execute('SELECT id, name FROM participants ORDER BY draft_order').fetchall()
    roster = {}
    for p in parts:
        row = db.execute('''
            SELECT pl.jersey_number, pl.name_cn, pl.name, s.round_number, s.pick_number
            FROM selections s
            JOIN players pl ON pl.id = s.player_id
            WHERE s.participant_id = ?
            ORDER BY s.round_number DESC, s.pick_number DESC
            LIMIT 1
        ''', (p['id'],)).fetchone()
        if row:
            roster[p['name']] = {
                'num': row['jersey_number'],
                'name': row['name_cn'] or row['name'],
                'pick_number': global_pick_number(row['round_number'], row['pick_number']),
                'top20': is_top20_pick(row['round_number'], row['pick_number']),
            }
        else:
            roster[p['name']] = None
    db.close()
    return roster


def get_selections_for_display(db=None):
    """Read-only selections for briefing / scorer matching."""
    close = False
    if db is None:
        db = get_db()
        close = True
    rows = db.execute('''
        SELECT p.name AS participant, pl.id AS player_id, pl.name_cn, pl.name,
               pl.jersey_number, t.name AS team_name, s.round_number, s.pick_number
        FROM selections s
        JOIN participants p ON p.id = s.participant_id
        JOIN players pl ON pl.id = s.player_id
        JOIN teams t ON t.id = pl.team_id
        ORDER BY s.round_number, s.pick_number
    ''').fetchall()
    if close:
        db.close()
    out = []
    for r in rows:
        item = dict(r)
        item['pick_number'] = global_pick_number(r['round_number'], r['pick_number'])
        item['top20'] = is_top20_pick(r['round_number'], r['pick_number'])
        out.append(item)
    return out


def open_db_readonly():
    conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_roster_for_team(team_name):
    """Per-participant all picks from team_name (list per person, or null)."""
    db = get_db()
    participants = db.execute('SELECT id, name FROM participants ORDER BY draft_order').fetchall()
    roster = {}
    for p in participants:
        rows = db.execute('''
            SELECT pl.jersey_number, pl.name_cn, pl.name, s.round_number, s.pick_number
            FROM selections s
            JOIN players pl ON pl.id = s.player_id
            JOIN teams t ON t.id = pl.team_id
            WHERE s.participant_id = ? AND t.name = ?
            ORDER BY s.round_number, s.pick_number
        ''', (p['id'], team_name)).fetchall()
        if rows:
            roster[p['name']] = [
                {
                    'num': row['jersey_number'],
                    'name': row['name_cn'] or row['name'],
                    'pick': global_pick_number(row['round_number'], row['pick_number']),
                    'top20': is_top20_pick(row['round_number'], row['pick_number']),
                }
                for row in rows
            ]
        else:
            roster[p['name']] = None
    db.close()
    return roster


def _resolve_match_odds(fixture_id, inline_odds=None):
    from briefing.odds_fetch import resolve_odds_for_fixture
    return resolve_odds_for_fixture(fixture_id, inline_odds)


def _find_briefing_match(briefing, fixture_id):
    for block in ('today', 'yesterday'):
        if block not in briefing:
            continue
        for m in briefing.get(block, {}).get('matches', []):
            if m.get('fixture_id') == fixture_id:
                return m
    return None


def get_match_detail(fixture_id):
    fixtures = {f['fixture_id']: f for f in load_fixtures()}
    fix = fixtures.get(fixture_id)
    if not fix:
        return None
    briefing = load_briefing_enriched()
    owner_map = get_owner_map()
    squad_meta = load_json(SQUAD_META_PATH, {})
    team_form = load_json(TEAM_FORM_PATH, {})

    match_info = _find_briefing_match(briefing, fixture_id)
    if not match_info:
        overrides = load_json(os.path.join(BRIEFING_DIR, 'news_overrides.json'), {})
        override_news = overrides.get(str(fixture_id))
        if override_news:
            match_info = {'key_news': override_news}

    home_owner = owner_display(fix['home_team'], owner_map)
    away_owner = owner_display(fix['away_team'], owner_map)
    photo = fix.get('stadium_photo', 'azteca.jpg')
    stadium_key = photo.replace('.jpg', '').replace('.jpeg', '')
    kickoff = fix.get('kickoff_beijing', '')
    kick_time = kickoff.split(' ')[-1] if kickoff else ''
    kick_date = kickoff.split(' ')[0] if kickoff else ''
    meta = f"Group {fix.get('group', '')} · Matchday {fix.get('matchday', '')} · 北京时间 {kick_date}"

    hs = match_info.get('home_score') if match_info else None
    aw = match_info.get('away_score') if match_info else None
    status = match_info.get('status', 'scheduled') if match_info else 'scheduled'
    if hs is not None and aw is not None:
        status_label = '已结束'
        score = f'{hs} — {aw}'
        status_class = 'finished'
    else:
        status_label = '即将开始'
        score = None
        status_class = ''

    return {
        'fixture_id': fixture_id,
        'stadium': fix.get('stadium'),
        'stadium_key': stadium_key,
        'stadium_photo': photo,
        'weather': fix.get('weather', ''),
        'temp': fix.get('temp', ''),
        'kickoff': kick_time,
        'meta': meta,
        'kickoff_beijing': kickoff,
        'home_team': fix['home_team'],
        'away_team': fix['away_team'],
        'home_flag': fix.get('home_flag', 'xx'),
        'away_flag': fix.get('away_flag', 'xx'),
        'home_owner': home_owner,
        'away_owner': away_owner,
        'home_score': hs,
        'away_score': aw,
        'status': status_label,
        'status_class': status_class,
        'score': score,
        'our_scorers': match_info.get('our_scorers', []) if match_info else [],
        'key_news': match_info.get('key_news', []) if match_info else [],
        'odds': _resolve_match_odds(fixture_id, match_info.get('odds') if match_info else None),
        'venue_context': fix.get('venue_context'),
        'home_travel': fix.get('home_travel'),
        'away_travel': fix.get('away_travel'),
        'home_meta': squad_meta.get(fix['home_team'], {}),
        'away_meta': squad_meta.get(fix['away_team'], {}),
        'home_form': team_form.get(fix['home_team']),
        'away_form': team_form.get(fix['away_team']),
        'home_roster': get_roster_for_team(fix['home_team']),
        'away_roster': get_roster_for_team(fix['away_team']),
    }


def history_dates_payload():
    idx = load_history_index()
    yesterday = yesterday_bj_str()
    dates = list_report_dates(idx)
    if yesterday in dates:
        default = yesterday
    elif dates:
        default = dates[0]
    else:
        default = None
    return {'dates': dates, 'default': default, 'yesterday': yesterday}
