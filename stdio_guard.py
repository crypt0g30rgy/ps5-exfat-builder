"""Make ``sys.stdout`` / ``sys.stderr`` safe to write in a windowed exe.

PyInstaller's ``--windowed`` build starts without valid console streams:
Python may set the streams to ``None``, or leave a wrapper whose
underlying file descriptor is invalid.  mkpfs and multiprocessing
children write progress to ``stderr``, so a missing or broken stream
turns into ``AttributeError`` / ``OSError: [Errno 22]`` and aborts a
build.

:func:`ensure_std_streams` probes both streams and rebinds only the
broken one.  It prefers the process's inherited stdout/stderr fd, then
falls back to the null device, so library code can always call
``.write()`` and ``.flush()``.
"""

from __future__ import annotations

import os
import sys

_NULL_DEVICE = 'nul' if os.name == 'nt' else os.devnull


def _stream_ok(stream):
    """Return True when *stream* accepts a tiny write and a flush."""
    if stream is None:
        return False
    try:
        stream.write('')
        stream.flush()
        return True
    except Exception:
        return False


def _fd_ok(fd):
    """Return True when *fd* refers to an open OS-level handle.

    A windowed build can leave fd 1/2 in the CRT table while the
    underlying Windows handle is invalid; wrapping that fd with
    ``os.fdopen`` succeeds but the first real write raises Errno 22.
    """
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False


def _bind_fd(fd):
    """Wrap an inherited fd as a UTF-8 text stream, or return None."""
    try:
        return os.fdopen(fd, 'w', encoding='utf-8', errors='replace',
                         buffering=1, closefd=False)
    except Exception:
        return None


def _open_null():
    try:
        return open(_NULL_DEVICE, 'w', encoding='utf-8', errors='replace',
                    buffering=1)
    except Exception:
        return None


def _discard(stream):
    if stream is None:
        return
    try:
        stream.close()
    except Exception:
        pass


def ensure_std_streams():
    """Rebind broken ``sys.stdout`` / ``sys.stderr`` streams.

    Returns the number of streams that were replaced (0 when healthy).
    """
    replaced = 0
    for name, fd in (('stdout', 1), ('stderr', 2)):
        if _stream_ok(getattr(sys, name, None)):
            continue
        # A wrapper can be created around an fd that still fails on the
        # first real write, so verify the replacement before installing
        # it rather than deferring the OSError to library code.
        new_stream = _bind_fd(fd) if _fd_ok(fd) else None
        if not _stream_ok(new_stream):
            _discard(new_stream)
            new_stream = _open_null()
        if not _stream_ok(new_stream):
            _discard(new_stream)
            continue
        setattr(sys, name, new_stream)
        replaced += 1
    return replaced
