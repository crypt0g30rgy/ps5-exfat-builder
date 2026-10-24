"""Unit tests for ui/process_supervisor.py.

Run from the repo root:

    python -m unittest discover -s tests -v

These tests are POSIX-oriented because the development host is Linux; the
Windows path (taskkill /T /F) shares the same state machine and is covered
by the manual validation matrix in the release notes.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from ui.process_supervisor import (
    ProcResult,
    combine_probes,
    file_size_probe,
    run_process,
)


def _wait_for_pid_file(path: str, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with open(path, 'r', encoding='ascii') as fh:
                value = fh.read().strip()
            if value:
                return int(value)
        except (OSError, ValueError):
            time.sleep(0.02)
    raise AssertionError('child pid file was never written: %s' % path)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _reap(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    try:
        os.waitpid(pid, 0)
    except OSError:
        pass


class TestRunProcess(unittest.TestCase):
    def test_normal_exit_streams_lines_in_order(self):
        lines = []
        result = run_process(
            [sys.executable, '-c',
             'import sys; [print("line-%d" % i) for i in range(5)]'],
            on_line=lines.append,
            idle_timeout=10,
            warn_after=None,
            poll_interval=0.02,
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.ok)
        self.assertEqual(lines, ['line-%d' % i for i in range(5)])
        self.assertEqual(result.output_lines, 5)
        self.assertFalse(result.pipe_orphaned)

    def test_callback_exception_does_not_break_reader(self):
        lines = []

        def on_line(line):
            lines.append(line)
            raise RuntimeError('deliberate callback failure')

        result = run_process(
            [sys.executable, '-c',
             'import sys; [print("x%d" % i) for i in range(4)]'],
            on_line=on_line,
            idle_timeout=10,
            warn_after=None,
            poll_interval=0.02,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(lines), 4)

    def test_spawn_failure_is_returned_not_raised(self):
        result = run_process(
            ['/definitely/not/a/real/executable-xyz'],
            idle_timeout=5,
            warn_after=None,
        )
        self.assertIsNone(result.returncode)
        self.assertIsNotNone(result.error)
        self.assertFalse(result.ok)

    def test_already_cancelled_never_starts(self):
        cancel = threading.Event()
        cancel.set()
        result = run_process(
            [sys.executable, '-c', 'import time; time.sleep(5)'],
            cancel_event=cancel,
            idle_timeout=10,
            warn_after=None,
        )
        self.assertTrue(result.cancelled)
        self.assertIsNone(result.returncode)

    def test_cancel_kills_grandchild_tree(self):
        with tempfile.TemporaryDirectory() as td:
            pidfile = os.path.join(td, 'pid')
            cancel = threading.Event()
            timer = threading.Timer(0.4, cancel.set)
            timer.start()
            try:
                result = run_process(
                    ['/bin/sh', '-c',
                     'sleep 30 & echo $! > "$1"; wait', 'sh', pidfile],
                    cancel_event=cancel,
                    idle_timeout=30,
                    warn_after=None,
                    poll_interval=0.05,
                    kill_grace=3.0,
                )
            finally:
                timer.cancel()

            self.assertTrue(result.cancelled)
            self.assertLess(result.duration, 10.0)
            grandchild = _wait_for_pid_file(pidfile)
            deadline = time.monotonic() + 3.0
            while _pid_alive(grandchild) and time.monotonic() < deadline:
                time.sleep(0.05)
            try:
                self.assertFalse(_pid_alive(grandchild),
                                 'grandchild survived cancellation')
            finally:
                _reap(grandchild)

    def test_idle_timeout_stops_silent_child(self):
        result = run_process(
            [sys.executable, '-c', 'import time; time.sleep(30)'],
            idle_timeout=0.6,
            warn_after=None,
            poll_interval=0.05,
            kill_grace=3.0,
        )
        self.assertTrue(result.idle_timeout)
        self.assertTrue(result.timed_out)
        self.assertLess(result.duration, 10.0)

    def test_probe_progress_prevents_idle_timeout(self):
        ticks = {'n': 0}

        def probe():
            ticks['n'] += 1
            return ticks['n']

        result = run_process(
            [sys.executable, '-c',
             'import time; time.sleep(1.2); print("finished")'],
            probe=probe,
            probe_min_delta=0,
            idle_timeout=0.5,
            warn_after=None,
            poll_interval=0.05,
        )
        self.assertEqual(result.returncode, 0)
        self.assertFalse(result.timed_out)
        self.assertGreater(ticks['n'], 5)

    def test_blocking_probe_cannot_stall_the_supervisor(self):
        # A wedged OSFMount/Dokan volume (or an offline network share) can
        # make shutil.disk_usage block for minutes.  The probe must not
        # stall the loop that kills a hung child.
        started = time.monotonic()
        result = run_process(
            [sys.executable, '-c', 'import time; time.sleep(0.4)'],
            probe=lambda: time.sleep(10),
            probe_timeout=0.15,
            idle_timeout=10,
            warn_after=None,
            poll_interval=0.02,
        )
        self.assertEqual(result.returncode, 0)
        self.assertLess(time.monotonic() - started, 5.0)

    def test_blocking_probe_does_not_disable_the_idle_watchdog(self):
        # Skipping stuck probe samples must leave the watchdog armed.
        started = time.monotonic()
        result = run_process(
            [sys.executable, '-c', 'import time; time.sleep(30)'],
            probe=lambda: time.sleep(10),
            probe_timeout=0.15,
            idle_timeout=0.6,
            warn_after=None,
            poll_interval=0.02,
            kill_grace=3.0,
        )
        self.assertTrue(result.idle_timeout)
        self.assertLess(time.monotonic() - started, 8.0)

    def test_warning_fires_once_for_one_quiet_stretch(self):
        warnings = []
        result = run_process(
            [sys.executable, '-c',
             'import time; time.sleep(1.0); print("done")'],
            idle_timeout=5,
            warn_after=0.2,
            on_warning=warnings.append,
            poll_interval=0.05,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(warnings), 1)
        self.assertTrue(result.warning_fired)

    def test_parent_exit_with_inherited_pipe_does_not_hang(self):
        """The original bug: shell exits but sleep still owns stdout."""
        with tempfile.TemporaryDirectory() as td:
            pidfile = os.path.join(td, 'pid')
            started = time.monotonic()
            result = run_process(
                ['/bin/sh', '-c',
                 'sleep 30 & echo $! > "$1"; echo done; exit 0',
                 'sh', pidfile],
                idle_timeout=30,
                warn_after=None,
                poll_interval=0.02,
                drain_grace=0.3,
            )
            elapsed = time.monotonic() - started

            self.assertEqual(result.returncode, 0)
            self.assertLess(elapsed, 5.0,
                            'run_process waited for pipe EOF like the old code')
            self.assertTrue(result.pipe_orphaned)
            # The supervisor deliberately does not kill a helper on a clean
            # exit; the test owns cleanup.
            pid = _wait_for_pid_file(pidfile)
            _reap(pid)

    def test_chunk_callback_receives_carriage_returns(self):
        chunks = []
        result = run_process(
            [sys.executable, '-c',
             'import sys; sys.stdout.write("10%\\r50%\\r100%\\n"); '
             'sys.stdout.flush()'],
            on_chunk=chunks.append,
            idle_timeout=10,
            warn_after=None,
            poll_interval=0.02,
        )
        self.assertEqual(result.returncode, 0)
        joined = ''.join(chunks)
        self.assertIn('10%', joined)
        self.assertIn('50%', joined)
        self.assertIn('100%', joined)

    def test_phase_aware_idle_timeout_callable(self):
        limit = {'v': 0.4}
        result = run_process(
            [sys.executable, '-c', 'import time; time.sleep(30)'],
            idle_timeout=lambda: limit['v'],
            warn_after=None,
            poll_interval=0.05,
            kill_grace=3.0,
        )
        self.assertTrue(result.idle_timeout)
        limit['v'] = None


    def test_input_text_is_written_and_pipe_closed(self):
        # format.com-style prompt: the child must receive the bytes AND
        # see EOF, otherwise it waits forever for another answer.
        result = run_process(
            [sys.executable, '-c',
             'import sys; data = sys.stdin.read(); '
             'print("got:" + data.replace("\\n", "|"))'],
            input_text='\n\n\n',
            idle_timeout=10,
            warn_after=None,
            poll_interval=0.02,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('got:', result.tail[0])
        self.assertEqual(result.tail[0].count('|'), 3)


class TestProbeHelpers(unittest.TestCase):
    def test_file_size_probe_tracks_growth(self):
        with tempfile.NamedTemporaryFile(delete=False) as fh:
            path = fh.name
        try:
            probe = file_size_probe(path)
            self.assertIsNone(probe())
            with open(path, 'ab') as fh:
                fh.write(b'x' * 100)
            self.assertEqual(probe(), 100)
        finally:
            os.unlink(path)

    def test_combine_probes_tolerates_failures(self):
        def boom():
            raise OSError('no such volume')

        probe = combine_probes(boom, lambda: 42)
        self.assertEqual(probe(), (None, 42))


if __name__ == '__main__':
    unittest.main()
