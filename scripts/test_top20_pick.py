#!/usr/bin/env python3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import unittest

from game_logic import PICKS_PER_ROUND, global_pick_number, is_top20_pick


class TestTop20Pick(unittest.TestCase):
    def test_global_pick_math(self):
        self.assertEqual(global_pick_number(1, 1), 1)
        self.assertEqual(global_pick_number(1, 5), 5)
        self.assertEqual(global_pick_number(2, 1), 6)
        self.assertEqual(global_pick_number(4, 5), 20)

    def test_top20_boundary(self):
        self.assertTrue(is_top20_pick(4, 5))   # global pick 20
        self.assertFalse(is_top20_pick(5, 1))    # global pick 21
        self.assertTrue(is_top20_pick(1, 3))     # global pick 3


if __name__ == '__main__':
    unittest.main()
