"""Unit tests for hardware.py (opt-in tuning heuristics)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hardware  # noqa: E402


class HardwareTests(unittest.TestCase):
    def test_cpu_count_is_positive(self):
        self.assertGreaterEqual(hardware.cpu_count(), 1)

    def test_ram_is_positive_when_available(self):
        ram = hardware.total_ram_gb()
        # CI containers can hide physical memory; None is allowed.
        if ram is not None:
            self.assertGreater(ram, 0)

    def test_profile_shape(self):
        profile = hardware.hardware_profile()
        self.assertIn('cpu_count', profile)
        self.assertIn('ram_gb', profile)

    def test_small_systems_get_two_workers(self):
        self.assertEqual(
            hardware.recommended_pfs_workers(9, ram_gb=4, cores=16), 2)

    def test_default_systems_keep_four(self):
        self.assertEqual(
            hardware.recommended_pfs_workers(9, ram_gb=16, cores=8), 4)

    def test_large_systems_scale_up(self):
        self.assertEqual(
            hardware.recommended_pfs_workers(9, ram_gb=32, cores=12), 6)
        self.assertEqual(
            hardware.recommended_pfs_workers(9, ram_gb=64, cores=24), 8)

    def test_core_limit_is_respected(self):
        # cores-1 caps the result; a 2-core box never gets 8 workers.
        self.assertEqual(
            hardware.recommended_pfs_workers(9, ram_gb=128, cores=2), 1)
        self.assertLessEqual(
            hardware.recommended_pfs_workers(1, ram_gb=128, cores=24), 23)

    def test_low_level_scaling_reduces_workers(self):
        high = hardware.recommended_pfs_workers(9, ram_gb=64, cores=24)
        low = hardware.recommended_pfs_workers(1, ram_gb=64, cores=24)
        self.assertLessEqual(low, high)
        self.assertGreaterEqual(low, 1)

    def test_bad_level_is_clamped(self):
        self.assertGreaterEqual(
            hardware.recommended_pfs_workers('nonsense', ram_gb=16, cores=8), 1)


if __name__ == '__main__':
    unittest.main()
