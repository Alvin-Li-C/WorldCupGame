#!/usr/bin/env python3
"""Write fixture_stadium_assignments.json and patch fixtures_2026.json stadium fields."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.fixture_stadiums import apply_stadiums_to_fixtures, save_assignments
from briefing.venue_travel import enrich_fixtures

FIXTURES_PATH = os.path.join(ROOT, 'data', 'fixtures_2026.json')


def main():
    payload = save_assignments()
    print(f'Wrote assignments: {len(payload["rows"])} group matches')

    with open(FIXTURES_PATH, encoding='utf-8') as f:
        data = json.load(f)
    fixtures = data.get('fixtures') or []
    patched, n = apply_stadiums_to_fixtures(fixtures, payload)
    data['fixtures'] = enrich_fixtures(patched)
    data['stadium_assignments'] = 'data/fixture_stadium_assignments.json'

    with open(FIXTURES_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    photos = {f.get('stadium_photo') for f in data['fixtures']}
    print(f'Patched {n} fixtures in {FIXTURES_PATH}')
    print(f'Unique stadium photos: {len(photos)}')
    sample = next(f for f in data['fixtures'] if f.get('home_team') == '荷兰' and f.get('away_team') == '日本')
    print('Sample 荷兰 vs 日本:', sample.get('stadium'), sample.get('stadium_photo'))


if __name__ == '__main__':
    main()
