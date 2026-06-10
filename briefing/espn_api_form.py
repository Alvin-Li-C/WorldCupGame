"""Build last-5 national-team form from ESPN site API (no HTML / WAF)."""

import json

import time

import urllib.error

import urllib.request



from briefing.espn_teams import ESPN_TEAM_CN, ESPN_TEAMS



_SITE = 'https://site.api.espn.com/apis/site/v2/sports/soccer'

_USER_AGENT = 'Mozilla/5.0 (compatible; WorldCupGame/1.0)'



HOST_TEAMS_CN = frozenset({'墨西哥', '美国', '加拿大'})



_WCQ_LEAGUES = (

    'fifa.worldq.uefa',

    'fifa.worldq.concacaf',

    'fifa.worldq.caf',

    'fifa.worldq.afc',

    'fifa.worldq.conmebol',

    'fifa.worldq.afc.conmebol',

    'fifa.worldq.concacaf.ofc',

    'fifa.worldq.ofc',

)



_WCQ_LEAGUE_SEASONS = tuple(

    (league, season)

    for league in _WCQ_LEAGUES

    for season in (2024, 2025)

)



# Core schedules cover most pre-tournament friendlies.

_CORE_LEAGUES = (

    ('fifa.friendly', 2025),

    ('fifa.friendly', 2026),

    ('fifa.world', 2026),

)



_EXTRA_LEAGUES = (

    ('caf.nations', 2025),

    ('caf.nations', 2026),

    ('uefa.nations', 2025),

    ('uefa.nations', 2026),

    ('concacaf.gold', 2025),

    ('concacaf.gold', 2026),

    ('concacaf.nations.league', 2025),

    ('concacaf.nations.league', 2026),

    ('conmebol.america', 2024),

    ('conmebol.america', 2025),

    ('afc.asian_cup', 2024),

    ('afc.asian_cup', 2025),

) + _WCQ_LEAGUE_SEASONS



ESPN_ID_CN = {str(eid): ESPN_TEAM_CN[eng] for eng, (eid, _) in ESPN_TEAMS.items()}



_STYLE_ATTACK_RATIO = 1.3

_STYLE_DEFENSE_RATIO = 0.8





def _score_int(score):

    if score is None:

        return None

    if isinstance(score, dict):

        raw = score.get('displayValue', score.get('value'))

        if raw is None:

            return None

        return int(float(raw))

    if isinstance(score, str) and score.strip().isdigit():

        return int(score.strip())

    try:

        return int(score)

    except (TypeError, ValueError):

        return None





def _fetch_json(url, retries=6, pause=2.0):

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





def fetch_team_schedule(league, team_id, season):

    url = f'{_SITE}/{league}/teams/{team_id}/schedule?season={season}'

    for attempt in range(3):

        try:

            data = _fetch_json(url, retries=4, pause=1.5 + attempt)

        except RuntimeError:

            data = None

        if data is not None:

            return data.get('events') or []

        time.sleep(3 * (attempt + 1))

    return []





def _parse_finished_match(event, team_id, cutoff_date, league=''):

    comp = (event.get('competitions') or [{}])[0]

    status = (comp.get('status') or {}).get('type') or {}

    if status.get('name') != 'STATUS_FULL_TIME' and not status.get('completed'):

        return None



    iso = (event.get('date') or '')[:10]

    if iso and iso > cutoff_date:

        return None



    competitors = comp.get('competitors') or []

    ours = None

    opp_score = None

    our_score = None

    for c in competitors:

        tid = str((c.get('team') or {}).get('id', ''))

        sc = _score_int(c.get('score'))

        if tid == team_id:

            ours = c

            our_score = sc

        else:

            opp_score = sc



    if ours is None or our_score is None or opp_score is None:

        return None



    if our_score > opp_score:

        ch = 'W'

    elif our_score < opp_score:

        ch = 'L'

    else:

        ch = 'D'



    return {

        'event_id': str(event.get('id', '')),

        'date': iso or event.get('date'),

        'char': ch,

        'gf': our_score,

        'ga': opp_score,

        'league': league,

        'is_wcq': league.startswith('fifa.worldq.'),

    }





def _collect_team_matches(team_id, league_seasons, cutoff_date, delay=0.8):

    rows = []

    seen = set()

    for league, season in league_seasons:

        for event in fetch_team_schedule(league, team_id, season):

            eid = str(event.get('id', ''))

            if eid and eid in seen:

                continue

            row = _parse_finished_match(event, team_id, cutoff_date, league=league)

            if not row:

                continue

            seen.add(eid)

            rows.append(row)

        time.sleep(delay)

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

        'source': 'espn-api',

    }





def _style_from_ratio(ratio):

    if ratio >= _STYLE_ATTACK_RATIO:

        return 'attack', '进攻型'

    if ratio <= _STYLE_DEFENSE_RATIO:

        return 'defense', '防守型'

    return 'balanced', '均衡型'





def rows_to_wcq_profile(rows, team_cn):

    if team_cn in HOST_TEAMS_CN:

        return {

            'host_exempt': True,

            'style_label': '主办国免预选赛',

        }



    wcq_rows = [r for r in rows if r.get('is_wcq')]

    if not wcq_rows:

        return None



    matches = len(wcq_rows)

    goals_for = sum(r['gf'] for r in wcq_rows)

    goals_against = sum(r['ga'] for r in wcq_rows)

    gf_per = round(goals_for / matches, 2)

    ga_per = round(goals_against / matches, 2)

    ratio = round(gf_per / ga_per, 2) if ga_per > 0 else float(gf_per)

    style, style_label = _style_from_ratio(ratio)



    return {

        'matches': matches,

        'goals_for': goals_for,

        'goals_against': goals_against,

        'gf_per_game': gf_per,

        'ga_per_game': ga_per,

        'ratio': ratio,

        'style': style,

        'style_label': style_label,

    }





def _merge_rows(*groups):

    merged = {}

    for rows in groups:

        for row in rows:

            key = row.get('event_id') or f"{row['date']}-{row['gf']}-{row['ga']}"

            merged[key] = row

    return sorted(merged.values(), key=lambda r: r['date'], reverse=True)





def _attach_wcq(form, wcq):

    if not form:

        return form

    out = dict(form)

    out['wcq'] = wcq

    return out





def _form_for_team(tid, team_cn, cutoff_date, delay=1.0):

    core = _collect_team_matches(tid, _CORE_LEAGUES, cutoff_date, delay=delay)

    extra = _collect_team_matches(

        tid, _EXTRA_LEAGUES, cutoff_date, delay=max(0.6, delay * 0.6),

    )

    rows = _merge_rows(core, extra)

    form = rows_to_form(rows)

    wcq = rows_to_wcq_profile(rows, team_cn)

    return rows, form, wcq





def fetch_wcq_profile(team_cn, team_id, cutoff_date='2026-06-11', delay=0.5):
    """Fetch WCQ-only profile for one team (lighter than full form rebuild)."""
    rows = _collect_team_matches(str(team_id), _WCQ_LEAGUE_SEASONS, cutoff_date, delay=delay)
    return rows_to_wcq_profile(rows, team_cn)


def enrich_form_wcq(form_data, cutoff_date='2026-06-11', delay=0.5):
    """Add or refresh wcq on an existing team_form dict."""
    out = dict(form_data)
    for eng, (eid, _) in ESPN_TEAMS.items():
        cn = ESPN_TEAM_CN[eng]
        wcq = fetch_wcq_profile(cn, eid, cutoff_date=cutoff_date, delay=delay)
        if cn not in out:
            out[cn] = {}
        row = dict(out[cn])
        row['wcq'] = wcq
        out[cn] = row
        label = wcq.get('style_label') if wcq else '—'
        print(f'  {eng}: {label}', flush=True)
    return out


def build_team_form_api(cutoff_date='2026-06-11'):

    out = {}

    missing = []

    weak = []



    for eng, (eid, _) in ESPN_TEAMS.items():

        tid = str(eid)

        cn = ESPN_TEAM_CN[eng]

        rows, form, wcq = _form_for_team(tid, cn, cutoff_date)

        if form and len(form.get('last5', '')) < 5:

            weak.append((eng, tid, cn))

        if form:

            out[cn] = _attach_wcq(form, wcq)

        else:

            missing.append(eng)

        wcq_hint = wcq.get('style_label') if wcq else '—'

        print(f'  {eng}: {form["last5"] if form else "—"} · {wcq_hint}', flush=True)



    for eng, tid, cn in weak:

        print(f'  retry {eng} (only {len(out[cn]["last5"])} matches)...', flush=True)

        rows, form, wcq = _form_for_team(tid, cn, cutoff_date, delay=2.0)

        if form and len(form.get('last5', '')) >= len(out.get(cn, {}).get('last5', '')):

            out[cn] = _attach_wcq(form, wcq)

            print(f'    -> {form["last5"]}', flush=True)



    if missing:

        print(f'espn-api missing form: {", ".join(missing)}', flush=True)

    return out


