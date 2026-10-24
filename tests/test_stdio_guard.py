"""Unit tests for stdio_guard.py (windowed-exe stream hardening)."""

from __future__ import annotations

import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stdio_guard  # noqa: E402


class _BrokenStream:
    def __init__(self, exc):
        self.exc = exc

    def write(self, _text):
        raise self.exc

    def flush(self):
        pass


class StreamCheckTest(unittest.TestCase):

    def test_none_is_not_ok(self):
        self.assertFalse(stdio_guard._stream_ok(None))

    def test_working_stream_is_ok(self):
        self.assertTrue(stdio_guard._stream_ok(io.StringIO()))

    def test_broken_streams_are_not_ok(self):
        for exc in (OSError(22, 'Invalid argument'), ValueError('closed'),
                    AttributeError('no write')):
            self.assertFalse(
                stdio_guard._stream_ok(_BrokenStream(exc)), exc)


class FdProbeTest(unittest.TestCase):

    def test_open_fd_is_ok(self):
        self.assertTrue(stdio_guard._fd_ok(1))

    def test_closed_fd_is_not_ok(self):
        fd = os.open(os.devnull, os.O_RDONLY)
        os.close(fd)
        self.assertFalse(stdio_guard._fd_ok(fd))


class EnsureStdStreamsTest(unittest.TestCase):

    def test_healthy_streams_are_untouched(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'stdout', out), \
                mock.patch.object(sys, 'stderr', err), \
                mock.patch.object(stdio_guard, '_bind_fd') as bind:
            self.assertEqual(stdio_guard.ensure_std_streams(), 0)
            bind.assert_not_called()
            self.assertIs(sys.stdout, out)
            self.assertIs(sys.stderr, err)

    def test_only_broken_stream_is_replaced(self):
        healthy = io.StringIO()
        replacement = io.StringIO()
        with mock.patch.object(sys, 'stdout', None), \
                mock.patch.object(sys, 'stderr', healthy), \
                mock.patch.object(stdio_guard, '_bind_fd',
                                  return_value=replacement) as bind:
            self.assertEqual(stdio_guard.ensure_std_streams(), 1)
            bind.assert_called_once_with(1)
            self.assertIs(sys.stdout, replacement)
            self.assertIs(sys.stderr, healthy)

    def test_fd_bind_falls_back_to_null_device(self):
        replacement_out, replacement_err = io.StringIO(), io.StringIO()
        broken = _BrokenStream(OSError(22, 'Invalid argument'))
        with mock.patch.object(sys, 'stdout', broken), \
                mock.patch.object(sys, 'stderr', broken), \
                mock.patch.object(stdio_guard, '_bind_fd',
                                  return_value=None), \
                mock.patch.object(stdio_guard, '_open_null',
                                  side_effect=[replacement_out,
                                               replacement_err]):
            self.assertEqual(stdio_guard.ensure_std_streams(), 2)
            self.assertIs(sys.stdout, replacement_out)
            self.assertIs(sys.stderr, replacement_err)

    def test_unrecoverable_stream_is_left_alone(self):
        broken = _BrokenStream(OSError(22, 'Invalid argument'))
        with mock.patch.object(sys, 'stdout', broken), \
                mock.patch.object(sys, 'stderr', io.StringIO()), \
                mock.patch.object(stdio_guard, '_bind_fd',
                                  return_value=None), \
                mock.patch.object(stdio_guard, '_open_null',
                                  return_value=None):
            self.assertEqual(stdio_guard.ensure_std_streams(), 0)
            self.assertIs(sys.stdout, broken)


if __name__ == '__main__':
    unittest.main()
