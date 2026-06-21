"""Fetch kickoff-hour weather from Open-Meteo (free, no API key)."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENUES_PATH = os.path.join(ROOT, 'data', 'stadium_venues.json')

ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
USER_AGENT = 'WorldCupGame/1.0'

# WMO weather code -> 中文简述
WMO_CN = {
    0: '晴',
    1: '大部晴朗',
    2: '局部多云',
    3: '多云',
    45: '雾',
    48: '雾凇',
    51: '小毛毛雨',
    53: '毛毛雨',
    55: '大毛毛雨',
    56: '冻毛毛雨',
    57: '冻毛毛雨',
    61: '小雨',
    63: '中雨',
    65: '大雨',
    66: '冻雨',
    67: '冻雨',
    71: '小雪',
    73: '中雪',
    75: '大雪',
    77: '雪粒',
    80: '小阵雨',
    81: '阵雨',
    82: '大阵雨',
    85: '小阵雪',
    86: '大阵雪',
    95: '雷暴',
    96: '雷暴伴小冰雹',
    99: '雷暴伴大冰雹',
}

RAIN_CODES = frozenset({51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99})


def load_venues() -> dict:
    with open(VENUES_PATH, encoding='utf-8') as f:
        return json.load(f)


def weather_label(code: int | None) -> str:
    if code is None:
        return '—'
    return WMO_CN.get(int(code), f'代码{code}')


def is_rainy(code: int | None, precip_mm: float | None) -> bool:
    if precip_mm is not None and precip_mm >= 0.2:
        return True
    return code is not None and int(code) in RAIN_CODES


def temp_band(temp_c: float | None) -> str:
    if temp_c is None:
        return 'unknown'
    if temp_c < 15:
        return 'cool'
    if temp_c < 25:
        return 'mild'
    if temp_c <= 30:
        return 'warm'
    return 'hot'


def temp_band_label(band: str) -> str:
    return {
        'cool': '偏冷 (<15°C)',
        'mild': '温和 (15–25°C)',
        'warm': '偏热 (25–30°C)',
        'hot': '炎热 (>30°C)',
        'unknown': '未知',
    }.get(band, band)


def _fetch_json(url: str, retries: int = 3) -> dict | None:
    last_err = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(last_err or f'fetch failed: {url}')


def _kickoff_utc(fixture: dict) -> datetime | None:
    utc = fixture.get('utc_date')
    if utc:
        try:
            dt = datetime.fromisoformat(utc.replace('Z', '+00:00'))
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    kb = fixture.get('kickoff_beijing') or ''
    if ' ' in kb:
        try:
            from briefing.time_utils import BJ
            local = datetime.strptime(kb, '%Y-%m-%d %H:%M').replace(tzinfo=BJ)
            return local.astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def stadium_key_for_fixture(fixture: dict) -> str | None:
    vc = fixture.get('venue_context') or {}
    key = vc.get('stadium_key')
    if key:
        return key
    photo = (fixture.get('stadium_photo') or '').replace('.jpg', '').replace('.jpeg', '')
    return photo or None


def _hourly_at_kickoff(data: dict, kickoff: datetime) -> dict | None:
    hourly = data.get('hourly') or {}
    times = hourly.get('time') or []
    if not times:
        return None
    target = kickoff.strftime('%Y-%m-%dT%H:00')
    idx = None
    for i, t in enumerate(times):
        if t == target:
            idx = i
            break
    if idx is None:
        # nearest hour
        best_i, best_d = None, 999
        for i, t in enumerate(times):
            try:
                dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                d = abs((dt - kickoff).total_seconds())
                if d < best_d:
                    best_d, best_i = d, i
            except ValueError:
                continue
        if best_i is None or best_d > 7200:
            return None
        idx = best_i
    return {
        'temp_c': hourly.get('temperature_2m', [None])[idx],
        'humidity_pct': hourly.get('relative_humidity_2m', [None])[idx],
        'weather_code': hourly.get('weather_code', [None])[idx],
        'precip_mm': hourly.get('precipitation', [None])[idx],
        'wind_kmh': hourly.get('wind_speed_10m', [None])[idx],
        'observed_at': times[idx],
    }


def fetch_weather_for_kickoff(lat: float, lon: float, kickoff_utc: datetime, *, now: datetime | None = None) -> dict:
    """Return normalized weather_detail for one kickoff."""
    now = now or datetime.now(timezone.utc)
    day = kickoff_utc.strftime('%Y-%m-%d')
    hourly = 'temperature_2m,relative_humidity_2m,weather_code,precipitation,wind_speed_10m'
    use_archive = kickoff_utc.date() < now.date()
    if use_archive:
        params = (
            f'latitude={lat}&longitude={lon}'
            f'&start_date={day}&end_date={day}'
            f'&hourly={hourly}&timezone=UTC'
        )
        base = ARCHIVE_URL
    else:
        # Forecast API rejects start_date/end_date together with forecast_days.
        params = (
            f'latitude={lat}&longitude={lon}'
            f'&hourly={hourly}&timezone=UTC&forecast_days=16'
        )
        base = FORECAST_URL
    data = _fetch_json(f'{base}?{params}')
    row = _hourly_at_kickoff(data, kickoff_utc)
    if not row:
        return {'source': 'open-meteo', 'error': 'no_hourly_match'}

    code = row.get('weather_code')
    temp = row.get('temp_c')
    precip = row.get('precip_mm') or 0
    detail = {
        'temp_c': round(float(temp), 1) if temp is not None else None,
        'humidity_pct': int(row['humidity_pct']) if row.get('humidity_pct') is not None else None,
        'weather_code': int(code) if code is not None else None,
        'precip_mm': round(float(precip), 2),
        'wind_kmh': round(float(row['wind_kmh']), 1) if row.get('wind_kmh') is not None else None,
        'observed_at': row.get('observed_at'),
        'source': 'open-meteo-archive' if use_archive else 'open-meteo-forecast',
        'is_rainy': is_rainy(code, precip),
        'temp_band': temp_band(temp),
        'condition_cn': weather_label(code),
    }
    return detail


def format_weather_fields(detail: dict) -> tuple[str, str]:
    if detail.get('error'):
        return '—', '—'
    cond = detail.get('condition_cn') or '—'
    temp = detail.get('temp_c')
    if temp is None:
        return cond, '—'
    return cond, f'{round(temp)}°C'


def enrich_fixture_weather(fixture: dict, venues: dict | None = None, *, pause: float = 0.35) -> dict:
    """Attach weather, temp, weather_detail to a fixture dict (in place)."""
    venues = venues if venues is not None else load_venues()
    key = stadium_key_for_fixture(fixture)
    kickoff = _kickoff_utc(fixture)
    if not key or not kickoff or key not in venues:
        return fixture
    v = venues[key]
    lat, lon = v.get('lat'), v.get('lon')
    if lat is None or lon is None:
        return fixture
    try:
        detail = fetch_weather_for_kickoff(float(lat), float(lon), kickoff)
        time.sleep(pause)
    except RuntimeError:
        return fixture
    if detail.get('error'):
        return fixture
    w, t = format_weather_fields(detail)
    fixture['weather'] = w
    fixture['temp'] = t
    fixture['weather_detail'] = detail
    return fixture
