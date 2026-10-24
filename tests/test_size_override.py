"""Unit tests for size_override.py (queue custom-size normalization)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from size_override import parse_size_override  # noqa: E402


class ParseSizeOverrideTest(unittest.TestCase):

    def test_none_and_blank_mean_no_override(self):
        for value in (None, '', '   '):
            parsed = parse_size_override(value)
            self.assertIsNone(parsed.gb, value)
            self.assertFalse(parsed.is_auto, value)
            self.assertFalse(parsed, value)

    def test_integer_and_numeric_strings(self):
        for value, expected in ((24, 24), ('24', 24), (' 24 ', 24),
                                ('24G', 24), ('24g', 24), ('24 GB', 24),
                                ('24gb', 24), (24.0, 24), ('24.0', 24)):
            parsed = parse_size_override(value)
            self.assertEqual(parsed.gb, expected, value)
            self.assertFalse(parsed.is_auto, value)
            self.assertTrue(parsed, value)

    def test_fractional_value_is_kept_but_renders_safely(self):
        parsed = parse_size_override(24.5)
        self.assertEqual(parsed.gb, 24.5)
        self.assertEqual(parsed.label, '24.5')

    def test_auto_sentinel(self):
        for value in ('auto', 'AUTO', ' Auto ', 'automatic', 'default'):
            parsed = parse_size_override(value)
            self.assertIsNone(parsed.gb, value)
            self.assertTrue(parsed.is_auto, value)
            self.assertEqual(parsed.label, 'Auto')
            self.assertTrue(parsed, value)

    def test_invalid_values(self):
        for value in ('garbage', '0', 0, -1, '-5', 'nan', 'inf',
                      True, False, [], {}):
            parsed = parse_size_override(value)
            self.assertIsNone(parsed.gb, value)
            self.assertFalse(parsed.is_auto, value)
            self.assertFalse(parsed, value)

    def test_percent_d_would_have_crashed_on_auto(self):
        # Regression guard for the queue-view crash: the old code did
        # ``'%d GB' % size_override_gb`` without normalizing the value.
        parsed = parse_size_override('auto')
        self.assertIsNone(parsed.gb)
        self.assertEqual(parsed.label, 'Auto')


if __name__ == '__main__':
    unittest.main()
