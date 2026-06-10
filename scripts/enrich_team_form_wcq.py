#!/usr/bin/env python3
"""Refresh wcq style profiles on existing team_form.json (WCQ leagues only)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.espn_api_form import enrich_form_wcq
from briefing.form_fetch import _merge_seed_row

FORM_PATH = os.path.join(ROOT, 'data', 'briefing', 'team_form.json')
CACHE_PATH = os.path.join(ROOT, 'data', 'briefing', 'team_form_espn.json')
SEED_PATH = os.path.join(ROOT, 'data', 'team_form_seed.json')
CUTOFF = '2026-06-11'


def main():
    with open(FORM_PATH, encoding='utf-8') as f:
        data = json.load(f)
    print('Enriching WCQ profiles...', flush=True)
    data = enrich_form_wcq(data, cutoff_date=CUTOFF, delay=0.5)
    if os.path.isfile(SEED_PATH):
        with open(SEED_PATH, encoding='utf-8') as f:
            seed = json.load(f)
        for team, row in seed.items():
            data[team] = _merge_seed_row(data.get(team), row)
    for path in (FORM_PATH, CACHE_PATH):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'Wrote {len(data)} teams -> {FORM_PATH}')


if __name__ == '__main__':
    main()
