"""Beijing (UTC+8) time helpers for briefing dates and kickoffs."""
from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))
# After last kickoff + buffer, treat matchday as done for preview roll (90'+ stoppage).
MATCHDAY_COMPLETE_BUFFER = timedelta(hours=2, minutes=45)


def now_bj():
    return datetime.now(BJ)


def today_bj_str():
    return now_bj().date().isoformat()


def yesterday_bj_str():
    return (now_bj().date() - timedelta(days=1)).isoformat()


def parse_utc(iso_str):
    """Parse football-data ISO UTC timestamp."""
    if not iso_str:
        return None
    s = iso_str.replace('Z', '+00:00')
    return datetime.fromisoformat(s)


def utc_to_bj(iso_str):
    dt = parse_utc(iso_str)
    return dt.astimezone(BJ) if dt else None


def beijing_date_from_utc(iso_str):
    """赛果日：按北京时间日历日（非 UTC 日）。"""
    dt = utc_to_bj(iso_str)
    return dt.date().isoformat() if dt else None


def beijing_datetime_str(iso_str):
    """'YYYY-MM-DD HH:MM' in Beijing."""
    dt = utc_to_bj(iso_str)
    return dt.strftime('%Y-%m-%d %H:%M') if dt else None


def fixture_beijing_date(fixture):
    """赛果日 / 开赛日：优先 kickoff_beijing 的日期部分。"""
    ko = fixture.get('kickoff_beijing', '')
    if ko:
        return ko.split(' ')[0]
    return fixture.get('played_date', '')


def parse_kickoff_beijing(kickoff: str):
    """Parse 'YYYY-MM-DD HH:MM' as timezone-aware Beijing datetime."""
    if not kickoff or ' ' not in kickoff:
        return None
    try:
        return datetime.strptime(kickoff, '%Y-%m-%d %H:%M').replace(tzinfo=BJ)
    except ValueError:
        return None


def last_kickoff_on_date(fixtures, date_str):
    """Latest kickoff_beijing on a Beijing calendar day."""
    last = None
    for f in fixtures:
        ko = f.get('kickoff_beijing') or ''
        if not ko.startswith(date_str):
            continue
        dt = parse_kickoff_beijing(ko)
        if dt and (last is None or dt > last):
            last = dt
    return last


def matchday_likely_complete(fixtures, date_str, now=None, buffer=MATCHDAY_COMPLETE_BUFFER):
    """True when the last kickoff of the day is far enough in the past (BJ time)."""
    now = now or now_bj()
    last = last_kickoff_on_date(fixtures, date_str)
    if not last:
        return False
    return now >= last + buffer
