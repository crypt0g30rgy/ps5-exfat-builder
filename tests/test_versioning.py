"""Unit tests for app_version.py (tag-derived release versioning)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_version import normalize_version, resolve_version  # noqa: E402


class NormalizeVersionTest(unittest.TestCase):

    def test_plain_and_prefixed_versions(self):
        for value, expected in (
                ('4.0.100', '4.0.100'),
                ('v4.0.100', '4.0.100'),
                ('V4.0.100', '4.0.100'),
                ('  v4.0.100  ', '4.0.100'),
                ('4.1', '4.1'),
                ('4.0.100-rc1', '4.0.100-rc1'),
                ('4.0.100+build5', '4.0.100+build5')):
            self.assertEqual(normalize_version(value), expected, value)

    def test_unusable_values_become_empty(self):
        for value in (None, '', '   ', 'v', 'latest', 'v4.0.100 extra',
                      '4.0.100\n5', [], {}, True):
            self.assertEqual(normalize_version(value), '', value)


class ResolveVersionTest(unittest.TestCase):

    def test_build_override_wins(self):
        self.assertEqual(resolve_version('3.6.4', 'v4.0.101'), '4.0.101')

    def test_source_fallback_when_override_missing_or_invalid(self):
        for override in (None, '', 'garbage', 'v'):
            self.assertEqual(resolve_version('4.0.100', override), '4.0.100',
                             override)

    def test_committed_default_has_no_override(self):
        import _build_version
        self.assertIsNone(_build_version.BUILD_VERSION)
        self.assertEqual(resolve_version('4.0.100',
                                         _build_version.BUILD_VERSION),
                         '4.0.100')


if __name__ == '__main__':
    unittest.main()
