#!/usr/bin/env python3
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from briefing.news_fetch import (
    build_team_hints,
    collect_news_items,
    prefilter_for_match,
    relevance_tier,
    score_candidate,
)


def load_config():
    with open(os.path.join(ROOT, 'data', 'scraper_config.json'), encoding='utf-8') as f:
        return json.load(f)


def _blob_relevant_for_match(text):
    lower = text.lower()
    return any(
        kw in text or kw in lower
        for kw in (
            '墨西哥', '南非', '世界杯', '美加墨',
            'mexico', 'south africa', 'world cup',
        )
    )


class TestNewsFetch(unittest.TestCase):
    def test_collect_has_configured_sources(self):
        items = collect_news_items(load_config(), max_per_source=5)
        self.assertGreater(len(items), 0, 'expected items from configured feeds')
        sources = {i['source'] for i in items}
        self.assertTrue(
            any('懂球帝' in s or '直播8' in s for s in sources),
            f'missing domestic sources: {sources}',
        )
        if not any('ESPN' in s or 'CBS' in s or 'Sky' in s or 'BBC' in s for s in sources):
            self.skipTest(f'international feeds unreachable: {sources}')
        for item in items:
            self.assertTrue(item.get('title'))
            self.assertNotEqual(item.get('source'), item.get('url'))

    def test_parse_rss_uses_label(self):
        from briefing.news_fetch import _parse_rss
        items = _parse_rss(
            'https://www.espn.com/espn/rss/soccer/news',
            max_items=3,
            label='ESPN Soccer',
        )
        if not items:
            self.skipTest('ESPN RSS unreachable from this network')
        self.assertEqual(items[0]['source'], 'ESPN Soccer')

    def test_english_team_headline_tier2(self):
        config = load_config()
        team_map = json.load(open(os.path.join(ROOT, 'data', 'team_name_map.json'), encoding='utf-8'))
        hints = build_team_hints('墨西哥', '南非', config, team_hints_en=['Mexico', 'South Africa'])
        title = 'Mexico aiming to restore its soccer standing at World Cup 2026'
        self.assertEqual(
            relevance_tier(title, hints, '墨西哥', '南非', team_map), 2, title,
        )

    def test_csl_coach_headlines_excluded(self):
        config = load_config()
        hints = build_team_hints('墨西哥', '南非', config)
        csl_titles = (
            '苏亚雷斯：以胜利为目标，休赛期稳定体系巩固防守',
            '乔迪：下半程目标完善体系，成绩或优于上半程',
        )
        team_map = json.load(open(os.path.join(ROOT, 'data', 'team_name_map.json'), encoding='utf-8'))
        for title in csl_titles:
            self.assertEqual(
                relevance_tier(title, hints, '墨西哥', '南非', team_map), 0, title,
            )
            score, _ = score_candidate(
                title, hints, config['news']['impact_keywords'],
                home_team='墨西哥', away_team='南非', team_map=team_map,
            )
            self.assertEqual(score, 0, title)
        scotland = '苏格兰门将谈世界杯：历经波折终迎重大时刻'
        self.assertEqual(
            relevance_tier(scotland, hints, '墨西哥', '南非', team_map), 0, scotland,
        )

    def test_prefilter_mexico_south_africa(self):
        config = load_config()
        picks = ['圣地亚哥·希门尼斯', '劳尔·希门尼斯']
        candidates = prefilter_for_match('墨西哥', '南非', config, our_picks=picks)
        self.assertGreater(len(candidates), 0)
        for c in candidates:
            blob = f"{c['title']} {c.get('snippet', '')}"
            self.assertTrue(_blob_relevant_for_match(blob), blob[:120])
            self.assertNotIn('休赛期', title)
            self.assertNotIn('下半程', title)


if __name__ == '__main__':
    unittest.main()
