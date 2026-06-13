#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from datetime import datetime, timezone, timedelta

from briefing.time_utils import BJ
from briefing_data import (
    all_fixtures_finished_on_date,
    history_dates_payload,
    list_report_dates,
    match_has_results,
    report_has_results,
    resolve_preview_date,
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


if __name__ == '__main__':
    unittest.main()
