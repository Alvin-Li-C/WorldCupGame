#!/usr/bin/env python3
"""CLI: add manual scorer map rule and rebuild history."""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.rebuild_scorers import rebuild_scorers_from_api
from briefing.scorer_match import add_manual_rule


def main():
    parser = argparse.ArgumentParser(description='Repair unmatched scorer via manual map')
    parser.add_argument('--api-name', required=True, help='API scorer English name')
    parser.add_argument('--team', required=True, help='API team name e.g. Senegal')
    parser.add_argument('--player-id', type=int, required=True)
    parser.add_argument('--api-scorer-id', type=int, default=None)
    parser.add_argument('--note', default='CLI repair')
    args = parser.parse_args()

    rule = add_manual_rule(
        player_id=args.player_id,
        api_scorer_en=args.api_name,
        team_api=args.team,
        api_scorer_id=args.api_scorer_id,
        note=args.note,
    )
    print('Rule saved:', json.dumps(rule, ensure_ascii=False))
    result = rebuild_scorers_from_api()
    print('Updated matches:', result.get('updated_matches'))


if __name__ == '__main__':
    main()
