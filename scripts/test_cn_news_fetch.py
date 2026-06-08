#!/usr/bin/env python3
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.news_fetch import collect_news_items, prefilter_for_match


def load_config():
    with open(os.path.join(ROOT, 'data', 'scraper_config.json'), encoding='utf-8') as f:
        return json.load(f)


class TestCnNewsFetch(unittest.TestCase):
    def test_collect_has_domestic_sources(self):
        items = collect_news_items(load_config(), max_per_source=5)
        self.assertGreater(len(items), 0, 'expected items from 懂球帝/直播8')
        sources = {i['source'] for i in items}
        self.assertTrue(
            any('懂球帝' in s or '直播8' in s for s in sources),
            f'unexpected sources: {sources}',
        )
        for item in items:
            self.assertTrue(item.get('title'))
            self.assertNotIn('espn.com', (item.get('source') or '').lower())
            self.assertNotIn('espn.com', (item.get('url') or '').lower())

    def test_prefilter_mexico_south_africa(self):
        config = load_config()
        picks = ['圣地亚哥·希门尼斯', '劳尔·希门尼斯']
        candidates = prefilter_for_match('墨西哥', '南非', config, our_picks=picks)
        self.assertGreater(len(candidates), 0)
        blob = ' '.join(c['title'] for c in candidates)
        self.assertTrue(
            '墨西哥' in blob or '南非' in blob or '世界杯' in blob,
            blob[:200],
        )


if __name__ == '__main__':
    unittest.main()
