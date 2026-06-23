"""Refresh lineups + starter_picks for today's preview matches and upload to PA."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.lineup_fetch import (
    enrich_latest_starter_picks,
    refresh_match_lineups,
)
from briefing_data import fixtures_on_date, load_fixtures, load_json, today_bj_str
from scripts.build_daily_briefing import load_config, upload_briefing


def main():
    fixtures = load_fixtures()
    latest = load_json(os.path.join(ROOT, 'data', 'briefing', 'latest.json'), {})
    preview_date = (latest.get('today') or {}).get('date') or today_bj_str()
    targets = fixtures_on_date(fixtures, preview_date)
    print(f'Preview date {preview_date}: {len(targets)} fixture(s)', flush=True)
    stats = refresh_match_lineups(targets, force=True)
    print(f'Lineups: {stats}', flush=True)
    n = enrich_latest_starter_picks(fixtures)
    print(f'Embedded starter_picks in {n} preview match(es)', flush=True)
    upload_briefing(load_config())


if __name__ == '__main__':
    main()
