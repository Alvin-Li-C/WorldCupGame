#!/usr/bin/env python3
"""Pre-upload / pre-commit check for briefing JSON integrity."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.validate import upload_summary, validate_briefing_payload
from briefing_data import HISTORY_PATH, LATEST_PATH, list_report_dates, load_json
from briefing.shooter_standings import STANDINGS_PATH as SHOOTER_STANDINGS_PATH
from briefing.standings import STANDINGS_PATH


def main():
    payload = {
        'latest': load_json(LATEST_PATH),
        'history_index': load_json(HISTORY_PATH),
        'standings_teams': load_json(STANDINGS_PATH),
        'standings_shooters': load_json(SHOOTER_STANDINGS_PATH),
    }
    print(upload_summary(payload))
    ok, errors = validate_briefing_payload(payload)
    hist = payload.get('history_index') or {}
    dates = list_report_dates(hist)
    stale = set(hist.get('dates') or []) - set(dates)
    if stale:
        errors.append(f'stale dates in index: {sorted(stale)}')
        ok = False
    if not ok:
        print('FAILED:')
        for err in errors:
            print(f'  - {err}')
        sys.exit(1)
    print('OK — safe to upload')


if __name__ == '__main__':
    main()
