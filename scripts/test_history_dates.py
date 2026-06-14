#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from datetime import datetime, timezone, timedelta

from briefing.time_utils import BJ
from briefing_data import (
    all_report_finished_fixture_ids,
    all_fixtures_finished_on_date,
    enrich_today_preview,
    get_match_detail,
    history_dates_payload,
    list_report_dates,
    match_has_results,
    report_has_results,
    resolve_preview_date,
    _find_briefing_match,
)


class TestHistoryDates(unittest.TestCase):
    def test_match_has_results(self):
        self.assertTrue(match_has_results({'home_score': 1, 'away_score': 0}))
        self.assertFalse(match_has_results({'home_score': None, 'away_score': 0}))

    def test_list_report_dates_filters_empty(self):
        idx = {
            'reports': {
                '2026-06-06': {'matches': [{'home_score': None, 'away_score': None}]},
                '2026-06-12': {'matches': [{'home_score': 2, 'away_score': 1}]},
            }
        }
        self.assertEqual(list_report_dates(idx), ['2026-06-12'])
        self.assertTrue(report_has_results(idx['reports']['2026-06-12']))
        self.assertFalse(report_has_results(idx['reports']['2026-06-06']))

    def test_history_dates_payload_empty(self):
        payload = history_dates_payload()
        self.assertIn('yesterday', payload)
        self.assertIsInstance(payload['dates'], list)

    def test_history_dates_payload_default_is_most_recent(self):
        idx = {
            'reports': {
                '2026-06-12': {'matches': [{'fixture_id': 1, 'home_score': 2, 'away_score': 0}]},
                '2026-06-14': {'matches': [{'fixture_id': 5, 'home_score': 1, 'away_score': 1}]},
            }
        }
        dates = list_report_dates(idx)
        self.assertEqual(dates, ['2026-06-14', '2026-06-12'])
        self.assertEqual(dates[0], '2026-06-14')

    def test_all_report_finished_fixture_ids(self):
        idx = {
            'reports': {
                '2026-06-12': {'matches': [
                    {'fixture_id': 1, 'home_score': 2, 'away_score': 0},
                    {'fixture_id': 2, 'home_score': None, 'away_score': None},
                ]},
            }
        }
        self.assertEqual(all_report_finished_fixture_ids(idx), {1})

    def test_enrich_today_preview_excludes_finished(self):
        latest = {
            'briefing_date': '2026-06-14',
            'today': {
                'date': '2026-06-14',
                'matches': [
                    {
                        'fixture_id': 5,
                        'kickoff_beijing': '2026-06-14 03:00',
                        'home_score': 1,
                        'away_score': 1,
                        'status': 'finished',
                    },
                ],
            },
        }
        enriched = enrich_today_preview(latest, reference_date='2026-06-14')
        ids = [m['fixture_id'] for m in enriched['today']['matches']]
        self.assertNotIn(5, ids)

    def test_resolve_preview_date_rolls_after_all_finished(self):
        fixtures = [
            {'fixture_id': 1, 'kickoff_beijing': '2026-06-12 03:00'},
            {'fixture_id': 2, 'kickoff_beijing': '2026-06-12 10:00'},
            {'fixture_id': 3, 'kickoff_beijing': '2026-06-13 03:00'},
            {'fixture_id': 4, 'kickoff_beijing': '2026-06-13 09:00'},
        ]
        preview, is_next = resolve_preview_date(fixtures, '2026-06-12', {1, 2})
        self.assertEqual(preview, '2026-06-13')
        self.assertTrue(is_next)

    def test_resolve_preview_date_keeps_today_while_incomplete(self):
        fixtures = [
            {'fixture_id': 1, 'kickoff_beijing': '2026-06-12 03:00'},
            {'fixture_id': 2, 'kickoff_beijing': '2026-06-12 10:00'},
            {'fixture_id': 3, 'kickoff_beijing': '2026-06-13 03:00'},
        ]
        now = datetime(2026, 6, 12, 9, 30, tzinfo=BJ)
        preview, is_next = resolve_preview_date(fixtures, '2026-06-12', {1}, now=now)
        self.assertEqual(preview, '2026-06-12')
        self.assertFalse(is_next)

    def test_resolve_preview_date_rolls_after_last_kickoff_buffer(self):
        fixtures = [
            {'fixture_id': 1, 'kickoff_beijing': '2026-06-12 03:00'},
            {'fixture_id': 2, 'kickoff_beijing': '2026-06-12 10:00'},
            {'fixture_id': 3, 'kickoff_beijing': '2026-06-13 03:00'},
        ]
        # 12:46 BJ: last kickoff 10:00 + 2h45m elapsed -> roll even without history
        now = datetime(2026, 6, 12, 12, 46, tzinfo=BJ)
        preview, is_next = resolve_preview_date(fixtures, '2026-06-12', set(), now=now)
        self.assertEqual(preview, '2026-06-13')
        self.assertTrue(is_next)

    def test_resolve_preview_date_keeps_during_live_match(self):
        fixtures = [
            {'fixture_id': 1, 'kickoff_beijing': '2026-06-12 03:00'},
            {'fixture_id': 2, 'kickoff_beijing': '2026-06-12 10:00'},
        ]
        now = datetime(2026, 6, 12, 11, 0, tzinfo=BJ)
        preview, is_next = resolve_preview_date(fixtures, '2026-06-12', set(), now=now)
        self.assertEqual(preview, '2026-06-12')
        self.assertFalse(is_next)

    def test_find_briefing_match_from_history_when_not_in_preview(self):
        briefing = {
            'today': {'date': '2026-06-15', 'matches': [
                {'fixture_id': 9, 'home_score': None, 'away_score': None},
            ]},
        }
        m = _find_briefing_match(briefing, 8)
        if m is None:
            self.skipTest('fixture 8 not in history_index.json')
        self.assertEqual(m['home_score'], 2)
        self.assertEqual(m['away_score'], 0)

    def test_get_match_detail_shows_score_for_finished_fixture(self):
        detail = get_match_detail(8)
        if detail is None:
            self.skipTest('fixture 8 not in fixtures_2026.json')
        self.assertEqual(detail.get('status'), '已结束')
        self.assertEqual(detail.get('score'), '2 — 0')


if __name__ == '__main__':
    unittest.main()
