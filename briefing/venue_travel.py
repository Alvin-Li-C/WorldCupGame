"""Stadium altitude and team travel (q1+q2 via World Cup base camp)."""
import json
import math
import os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STADIUM_VENUES_PATH = os.path.join(ROOT, 'data', 'stadium_venues.json')
TEAM_BASES_PATH = os.path.join(ROOT, 'data', 'team_world_cup_bases.json')

ALTITUDE_TIERS = (
    ('extreme', 2000, '高原球场'),
    ('high', 1500, '亚高原'),
)


def load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), -2)


def photo_to_stadium_key(photo):
    if not photo:
        return None
    return photo.replace('.jpg', '').replace('.jpeg', '')


def venue_context_for_photo(photo, venues=None):
    venues = venues or load_json(STADIUM_VENUES_PATH, {})
    key = photo_to_stadium_key(photo)
    if not key or key not in venues:
        return {}
    v = venues[key]
    alt = v.get('altitude_m', 0)
    tier, label = 'normal', None
    for tname, threshold, tlabel in ALTITUDE_TIERS:
        if alt >= threshold:
            tier, label = tname, tlabel
            break
    return {
        'stadium_key': key,
        'altitude_m': alt,
        'altitude_tier': tier,
        'altitude_label': label,
    }


def _parse_kickoff(kickoff_beijing):
    if not kickoff_beijing:
        return None
    try:
        return datetime.strptime(kickoff_beijing[:16], '%Y-%m-%d %H:%M')
    except ValueError:
        try:
            return datetime.strptime(kickoff_beijing[:10], '%Y-%m-%d')
        except ValueError:
            return None


def _timezone_delta_h(tz_a, tz_b):
    if not tz_a or not tz_b or tz_a == tz_b:
        return 0
    try:
        from zoneinfo import ZoneInfo
        from briefing.time_utils import now_bj

        ref = now_bj().replace(month=6, day=15, hour=12, minute=0, second=0, microsecond=0)
        off_a = ref.replace(tzinfo=ZoneInfo(tz_a)).utcoffset()
        off_b = ref.replace(tzinfo=ZoneInfo(tz_b)).utcoffset()
        if off_a is None or off_b is None:
            return 0
        return int((off_b - off_a).total_seconds() // 3600)
    except Exception:
        return 0


def travel_label(distance_km, q1_km, q2_km, is_home_first_match=False, rest_days=None):
    if is_home_first_match and q2_km < 100:
        label = '主场作战'
    elif q1_km == 0:
        label = '赛会首战'
    elif distance_km < 500:
        label = f'短途 {int(distance_km)}km'
    else:
        label = f'远征 {int(distance_km)}km'
    if q1_km >= 1500 and q2_km >= 1500:
        label += ' · 往返大本营'
    return label


def compute_team_travel(team_name, fixture, prev_fixture, venues, bases, venue_coords):
    base = (bases or {}).get(team_name)
    if not base or base.get('lat') is None:
        return {'label': '大本营待补', 'distance_km': None, 'q1_km': None, 'q2_km': None}

    this_venue = venue_coords.get(fixture.get('fixture_id'))
    if not this_venue:
        return {'label': '球场待补', 'distance_km': None, 'q1_km': None, 'q2_km': None}

    base_lat, base_lon = base['lat'], base['lon']
    q2_km = haversine_km(base_lat, base_lon, this_venue['lat'], this_venue['lon'])

    if prev_fixture:
        prev_venue = venue_coords.get(prev_fixture['fixture_id'])
        if prev_venue:
            q1_km = haversine_km(prev_venue['lat'], prev_venue['lon'], base_lat, base_lon)
        else:
            q1_km = 0
        prev_ko = _parse_kickoff(prev_fixture.get('kickoff_beijing'))
        this_ko = _parse_kickoff(fixture.get('kickoff_beijing'))
        rest_days = (this_ko.date() - prev_ko.date()).days if prev_ko and this_ko else None
        tz_delta = _timezone_delta_h(prev_venue.get('timezone') if prev_venue else None, this_venue.get('timezone'))
    else:
        q1_km = 0
        rest_days = None
        tz_delta = _timezone_delta_h(base.get('timezone'), this_venue.get('timezone'))

    distance_km = q1_km + q2_km
    is_home = team_name == fixture.get('home_team')
    label = travel_label(distance_km, q1_km, q2_km, is_home_first_match=(is_home and not prev_fixture))

    out = {
        'label': label,
        'distance_km': int(distance_km),
        'q1_km': int(q1_km),
        'q2_km': int(q2_km),
        'base_label': base.get('base_label') or base.get('base_city', ''),
        'rest_days': rest_days,
    }
    if tz_delta:
        out['timezone_delta_h'] = tz_delta
    return out


def build_team_fixture_timeline(fixtures):
    """team_name -> list of fixtures sorted by kickoff."""
    timeline = {}
    sorted_fix = sorted(fixtures, key=lambda f: f.get('kickoff_beijing', ''))
    for f in sorted_fix:
        for team in (f.get('home_team'), f.get('away_team')):
            if team:
                timeline.setdefault(team, []).append(f)
    return timeline


def enrich_fixtures(fixtures, venues_path=STADIUM_VENUES_PATH, bases_path=TEAM_BASES_PATH):
    venues = load_json(venues_path, {})
    bases = load_json(bases_path, {})
    timeline = build_team_fixture_timeline(fixtures)

    venue_coords = {}
    for f in fixtures:
        fid = f.get('fixture_id')
        key = photo_to_stadium_key(f.get('stadium_photo'))
        if key and key in venues:
            v = venues[key]
            venue_coords[fid] = {
                'lat': v['lat'],
                'lon': v['lon'],
                'timezone': v.get('timezone'),
            }

    travel_by_team_fixture = {}
    for team, flist in timeline.items():
        cumulative = 0
        for i, f in enumerate(flist):
            prev = flist[i - 1] if i > 0 else None
            travel = compute_team_travel(team, f, prev, venues, bases, venue_coords)
            cumulative += travel.get('distance_km') or 0
            travel['cumulative_km'] = cumulative
            travel_by_team_fixture[(team, f['fixture_id'])] = travel

    for f in fixtures:
        fid = f.get('fixture_id')
        f['venue_context'] = venue_context_for_photo(f.get('stadium_photo'), venues)
        home, away = f.get('home_team'), f.get('away_team')
        f['home_travel'] = travel_by_team_fixture.get((home, fid), {}) if home else {}
        f['away_travel'] = travel_by_team_fixture.get((away, fid), {}) if away else {}

    return fixtures
