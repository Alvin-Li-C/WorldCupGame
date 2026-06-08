#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing_data import (
    history_dates_payload,
    list_report_dates,
    match_has_results,
    report_has_results,
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


if __name__ == '__main__':
    unittest.main()
