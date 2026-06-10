#!/usr/bin/env python3
"""Fetch last-5 form for 48 WC teams from ESPN results pages."""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.form_fetch import _merge_seed_row
from briefing.espn_api_form import build_team_form_api

OUT_CACHE = os.path.join(ROOT, 'data', 'briefing', 'team_form_espn.json')
OUT_FORM = os.path.join(ROOT, 'data', 'briefing', 'team_form.json')
SEED_PATH = os.path.join(ROOT, 'data', 'team_form_seed.json')
CUTOFF = '2026-06-11'


def main():
    print('Fetching last-5 form via ESPN site API...', flush=True)
    out = build_team_form_api(cutoff_date=CUTOFF)
    if os.path.isfile(SEED_PATH):
        with open(SEED_PATH, encoding='utf-8') as f:
            seed = json.load(f)
        for team, row in seed.items():
            out[team] = _merge_seed_row(out.get(team), row)
    os.makedirs(os.path.dirname(OUT_FORM), exist_ok=True)
    with open(OUT_CACHE, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open(OUT_FORM, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\nWrote {len(out)} teams -> {OUT_FORM}')


if __name__ == '__main__':
    main()
