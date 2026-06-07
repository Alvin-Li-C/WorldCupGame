#!/usr/bin/env python3
"""Audit drafted player English names vs wc_squads.json roster."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.scorer_match import normalize_player_name
from briefing_data import get_selections_for_display, load_json

SQUADS_PATH = os.path.join(ROOT, 'data', 'wc_squads.json')
TEAM_MAP_PATH = os.path.join(ROOT, 'data', 'team_name_map.json')


def cn_to_api_team(cn_name, team_map):
    for api, cn in team_map.items():
        if cn == cn_name:
            return api
    return None


def main():
    squads = load_json(SQUADS_PATH, {})
    team_map = load_json(TEAM_MAP_PATH, {})
    selections = get_selections_for_display()

    missing = []
    ok = 0
    for s in selections:
        api_team = cn_to_api_team(s['team_name'], team_map)
        roster = squads.get(api_team or '', [])
        norm_sel = normalize_player_name(s.get('name') or '')
        roster_norm = {normalize_player_name(n) for n in roster}
        if norm_sel in roster_norm:
            ok += 1
        else:
            missing.append({
                'player_id': s['player_id'],
                'name': s.get('name'),
                'name_cn': s.get('name_cn'),
                'team': s['team_name'],
                'api_team': api_team,
            })

    print(f'Selections: {len(selections)} | in squad: {ok} | missing: {len(missing)}')
    if missing:
        print(json.dumps(missing, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
