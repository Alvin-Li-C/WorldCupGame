"""Backfill ESPN starting lineups for all finished matches in history."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.lineup_fetch import backfill_finished_lineups, load_lineup_cache
from briefing_data import load_fixtures


def main():
    fixtures = load_fixtures()
    before = sum(1 for v in load_lineup_cache().values() if v.get('available'))
    print(f'Lineups before: {before}', flush=True)
    stats = backfill_finished_lineups(fixtures)
    after = sum(1 for v in load_lineup_cache().values() if v.get('available'))
    print(
        f"Done — checked {stats['checked']}, new {stats['updated']}, "
        f"available {stats['available']}, pending {stats['pending']}, total cached {after}",
        flush=True,
    )


if __name__ == '__main__':
    main()
