"""Beijing (UTC+8) time helpers for briefing dates and kickoffs."""
from datetime import datetime, timedelta, timezone

BJ = timezone(timedelta(hours=8))


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
