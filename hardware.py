"""Hardware detection helpers used for opt-in performance tuning.

Pure enough to unit-test on Linux (no Tkinter/Windows imports at module
level).  RAM detection uses Win32 ``GlobalMemoryStatusEx`` on Windows,
``os.sysconf`` on POSIX, and ``/proc/meminfo`` as a final fallback.

These helpers only take effect when the user opts in (the "Auto-tune
compression workers" setting or ``auto`` copy threads).  Defaults stay
deliberately conservative.
"""

import ctypes
import os
import sys

__all__ = [
    'cpu_count',
    'total_ram_gb',
    'hardware_profile',
    'recommended_pfs_workers',
]


def cpu_count():
    """Logical CPU count, always >= 1."""
    try:
        return max(1, int(os.cpu_count() or 1))
    except Exception:
        return 1


def _ram_gb_windows():
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ('dwLength', ctypes.c_ulong),
            ('dwMemoryLoad', ctypes.c_ulong),
            ('ullTotalPhys', ctypes.c_ulonglong),
            ('ullAvailPhys', ctypes.c_ulonglong),
            ('ullTotalPageFile', ctypes.c_ulonglong),
            ('ullAvailPageFile', ctypes.c_ulonglong),
            ('ullTotalVirtual', ctypes.c_ulonglong),
            ('ullAvailVirtual', ctypes.c_ulonglong),
            ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        raise OSError('GlobalMemoryStatusEx failed')
    return stat.ullTotalPhys / float(1024 ** 3)


def _ram_gb_posix():
    try:
        pages = os.sysconf('SC_PHYS_PAGES')
        page_size = os.sysconf('SC_PAGE_SIZE')
        if pages > 0 and page_size > 0:
            return (pages * page_size) / float(1024 ** 3)
    except (ValueError, OSError, AttributeError):
        pass
    try:
        with open('/proc/meminfo', 'r', encoding='ascii') as fh:
            for line in fh:
                if line.startswith('MemTotal:'):
                    kb = int(line.split()[1])
                    return kb / float(1024 ** 2)
    except Exception:
        pass
    return None


def total_ram_gb():
    """Total physical RAM in GiB, or ``None`` when it cannot be read."""
    try:
        if sys.platform.startswith('win'):
            return _ram_gb_windows()
        return _ram_gb_posix()
    except Exception:
        return None


def hardware_profile():
    """Return ``{'cpu_count': int, 'ram_gb': float|None}``."""
    return {'cpu_count': cpu_count(), 'ram_gb': total_ram_gb()}


def recommended_pfs_workers(level=9, ram_gb=None, cores=None):
    """Opt-in worker count for mkpfs compression.

    The conservative default (auto-tune off) remains ``_pfs_pack_tuning``'s
    cap of 4.  When the user enables auto-tuning we scale with available
    RAM and cores, then apply the same per-level scaling used by the
    conservative path:

        < 8 GiB RAM          -> 2 workers
        >= 32 GiB, >= 12 CPU -> 6 workers
        >= 64 GiB, >= 24 CPU -> 8 workers
        otherwise            -> 4 workers

    Never exceeds ``cores - 1`` and never returns less than 1.
    """
    if ram_gb is None:
        ram_gb = total_ram_gb()
    if cores is None:
        cores = cpu_count()
    cores = max(1, int(cores or 1))
    try:
        level = max(1, min(9, int(level)))
    except Exception:
        level = 9

    if ram_gb is not None and ram_gb < 8:
        base = 2
    elif ram_gb is not None and ram_gb >= 64 and cores >= 24:
        base = 8
    elif ram_gb is not None and ram_gb >= 32 and cores >= 12:
        base = 6
    else:
        base = 4

    ceil = max(1, min(base, cores - 1) if cores > 1 else 1)
    frac = 0.5 + 0.5 * (level - 1) / 8.0
    cap = max(2, int(round(ceil * frac))) if ceil >= 2 else 1
    return max(1, min(ceil, cap))
