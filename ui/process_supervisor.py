"""ui/process_supervisor.py — bounded, cancellable child-process execution.

Why this module exists
----------------------
The build pipeline shells out to robocopy (through the generated .bat/.ps1),
UFS2Tool and mkpfs.  The old call sites used::

    for line in proc.stdout:
        ...
    proc.wait()

That pattern has two fatal problems:

1. It waits for *pipe EOF*, not process exit.  If a child (or a grandchild
   such as an OSFMount helper) inherits the stdout handle and keeps it open,
   the loop never ends even though the tool we care about has exited.
2. There is no timeout and no cancellation.  One wedged tool blocks the
   whole queue for hours and closing the window does not stop it.

``run_process`` instead runs a daemon reader thread, waits on
``Popen.poll()`` (process exit) in the caller's thread, and can kill the
entire process tree on cancellation, an idle timeout, or a hard timeout.
Callbacks are deliberately tiny and must be thread-safe: they are invoked
from the reader thread.

Typical use::

    cancel = threading.Event()
    result = run_process(
        cmd,
        on_line=queue.put,                       # must be fast/thread-safe
        cancel_event=cancel,
        idle_timeout=45 * 60,                    # None disables
        warn_after=5 * 60,                       # None disables
        on_warning=lambda idle: log('no output for %ds' % idle),
        probe=volume_used_probe('E:\\\\'),       # bytes copied so far
    )
    if result.cancelled:
        ...
    elif result.timed_out:
        ...
    else:
        rc = result.returncode

Progress probes
---------------
A probe is a zero-argument callable returning a number (or a tuple of
numbers).  Every increase/decrease larger than ``probe_min_delta`` counts as
progress and resets the idle watchdog.  This is what lets a long, quiet
robocopy or mkpfs run survive the 45-minute idle limit: pass a probe for
the output file size, the destination volume's used bytes, or both via
``combine_probes``.  Probe failures are ignored so a transient sharing
violation can never crash the supervisor.

Probes are evaluated on a daemon worker thread and the supervision loop
waits at most ``probe_timeout`` seconds for a reading.  This matters: a
wedged OSFMount/Dokan volume or an offline network share can make
``shutil.disk_usage`` block for minutes, and a probe that stalls the loop
would also stall the idle watchdog that exists to kill a hung child.
"""

from __future__ import annotations

import codecs
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

__all__ = [
    'DEFAULT_IDLE_TIMEOUT',
    'DEFAULT_WARN_AFTER',
    'ProcResult',
    'run_process',
    'kill_process_tree',
    'terminate_all',
    'active_pids',
    'file_size_probe',
    'volume_used_probe',
    'combine_probes',
]

#: A silent external tool is presumed stuck after this long.  Games on a
#: slow HDD can go quiet during robocopy's summary phase, so call sites that
#: cannot supply a probe should use a longer value or None.
DEFAULT_IDLE_TIMEOUT = 45 * 60

#: Emit one warning when the child has produced no output/progress for this
#: long.  Purely informational; the kill only happens at the idle timeout.
DEFAULT_WARN_AFTER = 5 * 60

#: Windows only: taskkill is given this long before we fall back to
#: Popen.kill().  taskkill itself has been known to wedge on a protected
#: process; never let that wedge the GUI a second time.
_TASKKILL_TIMEOUT = 15.0

#: After the process exits, give the reader thread this long to drain the
#: last bytes.  If a grandchild still owns the pipe we stop waiting, close
#: our end, and return — the original hang this module prevents.
_DRAIN_GRACE = 3.0

_CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


# ──────────────────────────────────────────────────────────────────────────
# Result object
# ──────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProcResult:
    """Outcome of :func:`run_process`.

    ``returncode`` is None when the process could not be started or was
    killed before a return code was available.  ``timed_out`` covers both
    the idle and hard watchdogs; the specific flag says which one fired.
    """

    returncode: int | None = None
    cancelled: bool = False
    idle_timeout: bool = False
    hard_timeout: bool = False
    error: str | None = None
    duration: float = 0.0
    idle_for: float = 0.0
    output_lines: int = 0
    tree_killed: bool = False
    pipe_orphaned: bool = False
    warning_fired: bool = False
    tail: tuple[str, ...] = field(default_factory=tuple)

    @property
    def timed_out(self) -> bool:
        return self.idle_timeout or self.hard_timeout

    @property
    def ok(self) -> bool:
        return (self.returncode == 0 and not self.cancelled
                and not self.timed_out and self.error is None)

    def summary(self) -> str:
        if self.error:
            return 'not started: %s' % self.error
        if self.cancelled:
            return 'cancelled after %.0fs' % self.duration
        if self.idle_timeout:
            return 'stopped after %.0fs with no progress' % self.idle_for
        if self.hard_timeout:
            return 'stopped at the %.0fs hard limit' % self.duration
        return 'exited with code %s after %.1fs' % (
            self.returncode, self.duration)


# ──────────────────────────────────────────────────────────────────────────
# Active-process registry (used by close-time cleanup)
# ──────────────────────────────────────────────────────────────────────────

_ACTIVE_LOCK = threading.Lock()
_ACTIVE: dict[int, subprocess.Popen] = {}


def _register(proc: subprocess.Popen) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE[proc.pid] = proc


def _unregister(proc: subprocess.Popen) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE.pop(proc.pid, None)


def active_pids() -> list[int]:
    """PIDs of children currently supervised by this module."""
    with _ACTIVE_LOCK:
        return list(_ACTIVE)


def terminate_all(grace: float = 8.0) -> int:
    """Kill every supervised child tree.  Returns the number attempted.

    Called from the app's close handler.  Each kill is best-effort and
    bounded, because shutdown must never itself hang.
    """
    with _ACTIVE_LOCK:
        procs = list(_ACTIVE.values())
    for proc in procs:
        try:
            kill_process_tree(proc, grace=grace)
        except Exception:
            pass
    return len(procs)


# ──────────────────────────────────────────────────────────────────────────
# Process-tree termination
# ──────────────────────────────────────────────────────────────────────────

def _taskkill(pid: int) -> bool:
    """Kill a Windows process tree.  Returns True if taskkill said OK."""
    try:
        completed = subprocess.run(
            ['taskkill', '/PID', str(pid), '/T', '/F'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=_TASKKILL_TIMEOUT,
            creationflags=_CREATE_NO_WINDOW,
        )
        return completed.returncode == 0
    except Exception:
        return False


def _wait_quiet(proc: subprocess.Popen, timeout: float) -> bool:
    """Wait up to *timeout* for the process to exit; True if it did."""
    try:
        proc.wait(timeout=max(0.0, timeout))
        return True
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return proc.poll() is not None


def kill_process_tree(proc: subprocess.Popen, grace: float = 8.0) -> bool:
    """Terminate *proc* and its descendants.  Never blocks indefinitely.

    Windows: ``taskkill /T /F`` first (the only reliable way to get
    robocopy/PowerShell children), with ``Popen.kill`` as a fallback.
    POSIX: signal the process group created by ``start_new_session``,
    escalating to SIGKILL after *grace* seconds.

    Returns True if a tree-kill command succeeded, False if we had to fall
    back to killing only the direct child.
    """
    if proc.poll() is not None:
        return False

    pid = proc.pid
    tree_killed = False

    if os.name == 'nt':
        tree_killed = _taskkill(pid)
        if not _wait_quiet(proc, min(grace, 5.0)):
            try:
                proc.kill()
            except Exception:
                pass
            _wait_quiet(proc, 3.0)
        return tree_killed

    # POSIX: the supervisor starts children with start_new_session=True,
    # so pid is also the process-group id.  Fall back to the direct child
    # when the group is already gone or was created elsewhere.
    try:
        pgid = os.getpgid(pid)
    except Exception:
        pgid = None

    if pgid is not None and pgid != os.getpgid(0):
        try:
            os.killpg(pgid, signal.SIGTERM)
            tree_killed = True
        except Exception:
            tree_killed = False

    if not _wait_quiet(proc, grace):
        if pgid is not None and pgid != os.getpgid(0):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except Exception:
                pass
        try:
            proc.kill()
        except Exception:
            pass
        _wait_quiet(proc, 3.0)

    return tree_killed


# ──────────────────────────────────────────────────────────────────────────
# Progress probe helpers
# ──────────────────────────────────────────────────────────────────────────

def file_size_probe(path: str) -> Callable[[], int | None]:
    """Probe for a growing output file (mkpfs/UFS2Tool images)."""

    def _probe() -> int | None:
        try:
            total = 0
            # The tool may write a sibling .part file first; watch both.
            for candidate in (path, path + '.part'):
                try:
                    total += os.path.getsize(candidate)
                except OSError:
                    pass
            return total if total else None
        except Exception:
            return None

    return _probe


def volume_used_probe(path: str) -> Callable[[], int | None]:
    """Probe for bytes used on the volume containing *path*.

    During a copy into a mounted image, used space rises, which gives the
    idle watchdog real evidence of progress even when robocopy is quiet.
    """

    def _probe() -> int | None:
        try:
            usage = shutil.disk_usage(path)
            return int(usage.used)
        except Exception:
            return None

    return _probe


def combine_probes(*probes: Callable[[], Any]) -> Callable[[], tuple]:
    """Combine several probes; any one changing counts as progress."""

    def _probe() -> tuple:
        values = []
        for fn in probes:
            try:
                values.append(fn())
            except Exception:
                values.append(None)
        return tuple(values)

    return _probe


def _probe_values(value: Any) -> Iterable[float]:
    """Normalise a probe result to a sequence of comparable numbers."""
    if value is None:
        return ()
    if isinstance(value, (int, float)):
        return (float(value),)
    if isinstance(value, (tuple, list)):
        return tuple(float(v) for v in value
                     if isinstance(v, (int, float)))
    return ()


class _BoundedProbe:
    """Evaluate a probe off the supervision loop with a bounded wait.

    One daemon worker thread lives for the duration of a ``run_process``
    call.  ``sample()`` hands it a request and waits at most *timeout*
    seconds.  While a call is still stuck no new request is issued, and
    its eventual result is discarded, so a stale reading taken minutes ago
    can never reset the idle watchdog after the fact.  A hard wedge leaks
    at most this one daemon thread.
    """

    def __init__(self, probe: Callable[[], Any], timeout: float):
        self._probe = probe
        self._timeout = max(0.05, float(timeout))
        self._lock = threading.Lock()
        self._request = threading.Event()
        self._ready = threading.Event()
        self._closed = False
        self._in_flight = False
        self._abandoned = False
        self._started_at = 0.0
        self._result: Any = None
        self._thread = threading.Thread(
            target=self._run, name='proc-probe', daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            self._request.wait()
            if self._closed:
                return
            self._request.clear()
            try:
                value = self._probe()
            except Exception:
                value = None
            with self._lock:
                self._result = value
                self._ready.set()

    def sample(self) -> tuple[bool, Any]:
        """Return ``(True, value)`` for a fresh reading, else ``(False, None)``.

        Never blocks for longer than the configured timeout.
        """
        with self._lock:
            if self._in_flight:
                if self._ready.is_set():
                    value = self._result
                    self._in_flight = False
                    self._ready.clear()
                    if self._abandoned:
                        self._abandoned = False
                        return False, None
                    return True, value
                if self._abandoned:
                    return False, None
                if time.monotonic() - self._started_at >= self._timeout:
                    self._abandoned = True
                    return False, None
            else:
                self._ready.clear()
                self._in_flight = True
                self._abandoned = False
                self._started_at = time.monotonic()
                self._request.set()
            wait_for = self._timeout - (time.monotonic() - self._started_at)

        if not self._ready.wait(max(0.0, wait_for)):
            with self._lock:
                if self._in_flight and not self._ready.is_set():
                    self._abandoned = True
            return False, None

        with self._lock:
            if not self._ready.is_set():
                return False, None
            value = self._result
            self._in_flight = False
            self._ready.clear()
            if self._abandoned:
                self._abandoned = False
                return False, None
            return True, value

    def close(self) -> None:
        """Stop the worker.  A probe still blocked inside itself is daemonic."""
        with self._lock:
            self._closed = True
        self._request.set()


# ──────────────────────────────────────────────────────────────────────────
# Supervisor
# ──────────────────────────────────────────────────────────────────────────

def _safe_call(fn: Callable | None, *args: Any) -> None:
    """Run a user callback without letting it break supervision."""
    if fn is None:
        return
    try:
        fn(*args)
    except Exception:
        # A UI/log callback must never kill the reader thread.  Swallow:
        # the alternative is a dead pipe and a child blocked on write.
        pass


def _current_limit(limit: float | Callable[[], float] | None,
                   fallback: float | None) -> float | None:
    """Resolve a possibly phase-aware timeout to a number of seconds."""
    if limit is None:
        return None
    if callable(limit):
        try:
            value = limit()
        except Exception:
            return fallback
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return fallback
        return value if value > 0 else None
    return float(limit)


def run_process(
    cmd: str | Sequence[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    on_line: Callable[[str], None] | None = None,
    on_chunk: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    idle_timeout: float | Callable[[], float | None] | None = DEFAULT_IDLE_TIMEOUT,
    hard_timeout: float | Callable[[], float | None] | None = None,
    warn_after: float | None = DEFAULT_WARN_AFTER,
    on_warning: Callable[[float], None] | None = None,
    probe: Callable[[], Any] | None = None,
    probe_min_delta: float = 0.0,
    probe_timeout: float | None = 2.0,
    poll_interval: float = 0.25,
    drain_grace: float = _DRAIN_GRACE,
    kill_grace: float = 8.0,
    encoding: str = 'utf-8',
    errors: str = 'replace',
    max_line_chars: int = 1024 * 1024,
    stdin: Any = subprocess.DEVNULL,
    input_text: str | None = None,
    creationflags: int | None = None,
    startupinfo: Any = None,
    start_new_session: bool | None = None,
    shell: bool = False,
    bufsize: int = 0,
    tail_lines: int = 40,
    **popen_kwargs: Any,
) -> ProcResult:
    """Run *cmd*, returning once the process has exited or was stopped.

    Parameters
    ----------
    on_line:
        Called from a daemon reader thread for each complete ``\\n`` line
        (without the newline).  Must be fast and thread-safe.  Use a queue
        to hand work to the Tk main thread.
    on_chunk:
        Called with decoded text as it arrives, including ``\\r`` progress
        updates.  Intended for mkpfs's carriage-return progress parser.
        Both callbacks may be supplied.
    cancel_event:
        Set it to request termination.  Checked every ``poll_interval`` and
        also used as the wait primitive, so cancellation is prompt.
    idle_timeout:
        Kill after this many seconds with no stdout and no probe progress.
        Pass ``None`` to disable.  May be a callable for phase-aware limits.
    hard_timeout:
        Absolute wall-clock limit for the child.  ``None`` disables.
    warn_after:
        Fire ``on_warning(idle_seconds)`` once per quiet stretch.  ``None``
        disables.
    probe:
        Zero-argument callable returning a number or tuple of numbers.
        Any change (greater than ``probe_min_delta``) resets the idle
        watchdog.  Failures are ignored.
    probe_timeout:
        Seconds to wait for a probe reading before skipping that tick.
        Defaults to 2s so a syscall wedged on a dead mount cannot stall
        the supervision loop.  Pass ``None`` to call the probe inline.
    stdin:
        Passed to Popen.  Defaults to DEVNULL.
    input_text:
        Short text written to the child's stdin immediately after launch
        (the pipe is then closed).  Used for tools such as format.com that
        insist on prompting even with /Y.  Keep it small: it must fit in
        the OS pipe buffer so this can never block the supervisor.
    creationflags / startupinfo:
        Passed to Popen.  On Windows the default is CREATE_NO_WINDOW.
    start_new_session:
        Defaults to True on POSIX so the whole group can be killed.

    Returns
    -------
    ProcResult
        Never raises for a child that failed to start; inspect ``error``.
    """
    started = time.monotonic()

    if cancel_event is not None and cancel_event.is_set():
        return ProcResult(cancelled=True, duration=0.0)

    if creationflags is None:
        creationflags = _CREATE_NO_WINDOW if os.name == 'nt' else 0
    if start_new_session is None:
        start_new_session = os.name != 'nt'

    popen_args: dict[str, Any] = dict(popen_kwargs)
    popen_args.update(
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE if input_text is not None else stdin,
        bufsize=bufsize,
        cwd=cwd,
        env=env,
        shell=shell,
        creationflags=creationflags,
        startupinfo=startupinfo,
        start_new_session=start_new_session,
    )
    # Don't pass Windows-only fields on POSIX when they are defaults.
    if os.name != 'nt':
        popen_args.pop('creationflags', None)
        popen_args.pop('startupinfo', None)

    try:
        proc = subprocess.Popen(cmd, **popen_args)
    except Exception as exc:
        return ProcResult(
            error='%s: %s' % (type(exc).__name__, exc),
            duration=time.monotonic() - started,
        )

    _register(proc)

    if input_text is not None:
        # Feed short, non-blocking stdin input (format.com prompts).
        try:
            proc.stdin.write(input_text.encode(encoding, errors=errors))
            proc.stdin.flush()
            proc.stdin.close()
        except Exception:
            pass

    state_lock = threading.Lock()
    tail: deque[str] = deque(maxlen=max(1, int(tail_lines)))
    line_count = 0
    last_activity = started
    last_probe: Any = None
    warned = False
    warning_fired = False
    stop_reader = threading.Event()
    reader_done = threading.Event()

    decoder = codecs.getincrementaldecoder(encoding)(errors=errors)
    text_buf = ''

    def _note_line(line: str) -> None:
        nonlocal line_count
        with state_lock:
            line_count += 1
            tail.append(line)
        _safe_call(on_line, line)

    def _emit_text(text: str) -> None:
        nonlocal text_buf
        if not text:
            return
        _safe_call(on_chunk, text)
        text_buf += text
        while True:
            nl = text_buf.find('\n')
            if nl < 0:
                break
            line = text_buf[:nl]
            text_buf = text_buf[nl + 1:]
            if line.endswith('\r'):
                line = line[:-1]
            _note_line(line)
        if len(text_buf) > max_line_chars:
            # Pathological output with no newline: emit what we have so the
            # UI still shows activity and memory stays bounded.
            line = text_buf
            text_buf = ''
            _note_line(line)

    def _reader() -> None:
        nonlocal last_activity
        stream = proc.stdout
        try:
            while not stop_reader.is_set():
                chunk = stream.read(65536)
                if not chunk:
                    break
                last_activity = time.monotonic()
                try:
                    text = decoder.decode(chunk)
                except Exception:
                    text = chunk.decode(encoding, errors='replace')
                if text:
                    _emit_text(text)
            try:
                tail_text = decoder.decode(b'', final=True)
                if tail_text:
                    _emit_text(tail_text)
            except Exception:
                pass
            if text_buf:
                _note_line(text_buf)
        except Exception:
            # Pipe closed under us (watchdog/shutdown) or decode failure.
            # Not an error worth surfacing: the main loop handles the
            # process state.
            pass
        finally:
            reader_done.set()

    reader = threading.Thread(
        target=_reader, name='proc-reader-%s' % proc.pid, daemon=True)
    reader.start()

    probe_runner = None
    if probe is not None and probe_timeout is not None:
        try:
            probe_runner = _BoundedProbe(probe, probe_timeout)
        except Exception:
            # Thread creation failed (resource exhaustion): fall back to
            # an inline probe rather than failing the whole run.
            probe_runner = None

    cancelled = False
    idle_timeout_hit = False
    hard_timeout_hit = False
    tree_killed = False
    pipe_orphaned = False

    def _stop_child() -> None:
        nonlocal tree_killed
        tree_killed = kill_process_tree(proc, grace=kill_grace)
        # Closing our end encourages an inherited-handle reader to finish.
        # The Popen process object is still valid for wait().
        try:
            proc.stdout.close()  # type: ignore[union-attr]
        except Exception:
            pass

    try:
        while True:
            rc = proc.poll()
            if rc is not None:
                break

            now = time.monotonic()
            elapsed = now - started

            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                _stop_child()
                if not _wait_quiet(proc, kill_grace):
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    _wait_quiet(proc, 3.0)
                break

            if probe is not None:
                if probe_runner is not None:
                    have_value, value = probe_runner.sample()
                else:
                    have_value = True
                    try:
                        value = probe()
                    except Exception:
                        value = None
                if have_value and value is not None:
                    current = tuple(_probe_values(value))
                    if last_probe is not None and current:
                        try:
                            changed = any(
                                abs(a - b) > probe_min_delta
                                for a, b in zip(current, last_probe)
                                if isinstance(a, (int, float))
                                and isinstance(b, (int, float))
                            )
                            if len(current) != len(last_probe):
                                changed = True
                        except Exception:
                            changed = False
                        if changed:
                            last_activity = now
                            warned = False
                    last_probe = current

            idle_for = now - last_activity

            if (warn_after is not None and not warned
                    and idle_for >= warn_after):
                warned = True
                warning_fired = True
                _safe_call(on_warning, idle_for)

            idle_limit = _current_limit(idle_timeout, DEFAULT_IDLE_TIMEOUT)
            if idle_limit is not None and idle_for >= idle_limit:
                idle_timeout_hit = True
                _stop_child()
                if not _wait_quiet(proc, kill_grace):
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    _wait_quiet(proc, 3.0)
                break

            hard_limit = _current_limit(hard_timeout, None)
            if hard_limit is not None and elapsed >= hard_limit:
                hard_timeout_hit = True
                _stop_child()
                if not _wait_quiet(proc, kill_grace):
                    try:
                        proc.kill()
                    except Exception:
                        pass
                    _wait_quiet(proc, 3.0)
                break

            if cancel_event is not None:
                cancel_event.wait(max(0.02, poll_interval))
            else:
                time.sleep(max(0.02, poll_interval))

        # The process is gone (or killed).  Wait briefly for the reader to
        # drain, then stop waiting: a grandchild holding the pipe must not
        # recreate the original hang.
        if not reader_done.wait(drain_grace):
            pipe_orphaned = True
            stop_reader.set()
            try:
                proc.stdout.close()  # type: ignore[union-attr]
            except Exception:
                pass
            # If this was a timeout/cancel we already killed the tree; for a
            # normal exit an inherited pipe is typically a helper process
            # that is about to finish.  Do not kill it unconditionally.
            reader_done.wait(1.0)

        try:
            returncode = proc.wait(timeout=5.0)
        except Exception:
            returncode = proc.poll()
    finally:
        stop_reader.set()
        if probe_runner is not None:
            probe_runner.close()
        _unregister(proc)
        try:
            if proc.poll() is not None:
                proc.stdout.close()  # type: ignore[union-attr]
        except Exception:
            pass

    now = time.monotonic()
    with state_lock:
        tail_snapshot = tuple(tail)
        line_total = line_count

    return ProcResult(
        returncode=returncode,
        cancelled=cancelled,
        idle_timeout=idle_timeout_hit,
        hard_timeout=hard_timeout_hit,
        duration=now - started,
        idle_for=now - last_activity,
        output_lines=line_total,
        tree_killed=tree_killed,
        pipe_orphaned=pipe_orphaned,
        warning_fired=warning_fired,
        tail=tail_snapshot,
    )
