#!/usr/bin/env python3
"""Unit tests for scorer matching (Senegal Ndiaye disambiguation)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.goal_events import event_points, extract_scoring_events
from briefing.scorer_build import build_match_scorers
from briefing.scorer_match import match_scorer_to_selection, normalize_player_name


def senegal_selections():
  return [
      {
          'player_id': 1001,
          'name': 'Cherif Ndiaye',
          'name_cn': '谢里夫·恩迪亚耶',
          'team_name': '塞内加尔',
          'participant': '庆爷',
          'jersey_number': 12,
          'pick_number': 40,
      },
      {
          'player_id': 1002,
          'name': 'Bara Sapoko Ndiaye',
          'name_cn': '巴拉·恩迪亚耶',
          'team_name': '塞内加尔',
          'participant': '庆爷',
          'jersey_number': 20,
          'pick_number': 41,
      },
      {
          'player_id': 1003,
          'name': 'Iliman Ndiaye',
          'name_cn': '伊利曼·恩迪亚耶',
          'team_name': '塞内加尔',
          'participant': '庆爷',
          'jersey_number': 23,
          'pick_number': 42,
      },
  ]


def _event(name, team_cn='塞内加尔', team_en='Senegal', scorer_id=None, gtype='REGULAR'):
    return {
        'scorer_en': name,
        'scorer_api_id': scorer_id,
        'team_cn': team_cn,
        'team_en': team_en,
        'type': gtype,
        'minute': 10,
    }


class TestScorerMatch(unittest.TestCase):
    def test_normalize_strips_accents(self):
        self.assertEqual(normalize_player_name('Kylian Mbappé'), 'kylian mbappe')

    def test_ndiaye_full_name_exact(self):
        sels = senegal_selections()
        for name, pid in [
            ('Cherif Ndiaye', 1001),
            ('Bara Sapoko Ndiaye', 1002),
            ('Iliman Ndiaye', 1003),
        ]:
            sel, reason = match_scorer_to_selection(_event(name), sels)
            self.assertEqual(reason, '', msg=name)
            self.assertEqual(sel['player_id'], pid, msg=name)

    def test_surname_only_ambiguous(self):
        sel, reason = match_scorer_to_selection(_event('Ndiaye'), senegal_selections())
        self.assertIsNone(sel)
        self.assertEqual(reason, 'ambiguous')

    def test_chinese_name_no_match(self):
        sel, reason = match_scorer_to_selection(
            {'scorer_en': '恩迪亚耶', 'team_cn': '塞内加尔', 'team_en': 'Senegal', 'type': 'REGULAR'},
            senegal_selections(),
        )
        self.assertIsNone(sel)
        self.assertIn(reason, ('no_name_match', 'ambiguous'))

    def test_own_goal_points(self):
        self.assertEqual(event_points({'type': 'OWN'}), (0, 1))
        self.assertEqual(event_points({'type': 'PENALTY'}), (1, 0))

    def test_build_match_three_scorers(self):
        team_map = {'Senegal': '塞内加尔', 'Netherlands': '荷兰'}
        api_match = {
            'homeTeam': {'name': 'Senegal'},
            'awayTeam': {'name': 'Netherlands'},
            'goals': [
                {'type': 'REGULAR', 'minute': 12, 'scorer': {'name': 'Cherif Ndiaye', 'id': 1},
                 'team': {'name': 'Senegal'}},
                {'type': 'REGULAR', 'minute': 34, 'scorer': {'name': 'Bara Sapoko Ndiaye', 'id': 2},
                 'team': {'name': 'Senegal'}},
                {'type': 'REGULAR', 'minute': 78, 'scorer': {'name': 'Iliman Ndiaye', 'id': 3},
                 'team': {'name': 'Senegal'}},
            ],
        }
        block = build_match_scorers(
            api_match, '塞内加尔', '荷兰', team_map, senegal_selections(),
            lambda en, m: m.get(en),
        )
        self.assertEqual(len(block['our_scorers']), 3)
        ids = {r['player_id'] for r in block['our_scorers']}
        self.assertEqual(ids, {1001, 1002, 1003})
        self.assertEqual(block['unmatched_scorers'], [])

    def test_penalty_shootout_not_in_goals(self):
        events = extract_scoring_events(
            {'homeTeam': {'name': 'A'}, 'awayTeam': {'name': 'B'}, 'goals': [], 'penalties': [{'scorer': {'name': 'X'}}]},
            {}, lambda *a: None,
        )
        self.assertEqual(events, [])

    def test_mexico_espn_fallback_scorers(self):
        import json
        import os
        from briefing.espn_goals import parse_espn_goal_events

        sample = os.path.join(ROOT, 'data', 'espn_mex_sa.json')
        with open(sample, encoding='utf-8') as f:
            summary = json.load(f)
        team_map = {'Mexico': '墨西哥', 'South Africa': '南非'}
        events = parse_espn_goal_events(
            summary, team_map, lambda en, m: m.get(en), 'Mexico', 'South Africa',
        )
        self.assertEqual(len(events), 2)
        sels = [
            {'player_id': 21, 'name': 'Julian Quinones', 'name_cn': '胡利安·基尼奥内斯',
             'team_name': '墨西哥', 'participant': '老王', 'jersey_number': 21},
            {'player_id': 22, 'name': 'Raul Jimenez', 'name_cn': '劳尔·希门尼斯',
             'team_name': '墨西哥', 'participant': '李总', 'jersey_number': 22},
        ]
        api_match = {
            'homeTeam': {'name': 'Mexico'},
            'awayTeam': {'name': 'South Africa'},
            'goals': None,
            'score': {'fullTime': {'home': 2, 'away': 0}},
            'utcDate': '2026-06-11T19:00:00Z',
        }
        block = build_match_scorers(
            api_match, '墨西哥', '南非', team_map, sels, lambda en, m: m.get(en),
        )
        self.assertEqual(len(block['our_scorers']), 2)
        ids = {r['player_id'] for r in block['our_scorers']}
        self.assertEqual(ids, {21, 22})


if __name__ == '__main__':
    unittest.main()
