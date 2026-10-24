"""Normalize per-queue-item custom image-size values.

``QueueItem.size_override_gb`` is normally an int, but queue JSON files
are user-editable and older builds also stored the string ``"auto"``.
Rendering those values with ``%d`` raises ``TypeError`` and takes the
whole queue view down, so every reader goes through this module.
"""

from __future__ import annotations

import math
from collections import namedtuple


class SizeOverride(namedtuple('_SizeOverride', 'gb is_auto')):
    """Parsed custom-size value.

    ``gb`` is a positive int/float, or ``None``.  ``is_auto`` is true for
    the explicit ``"auto"`` sentinel, which means "ignore the global
    Advanced override and let the allocator choose the smallest safe
    size".
    """

    __slots__ = ()

    @property
    def label(self):
        return 'Auto' if self.is_auto else str(self.gb)

    def __bool__(self):
        return self.gb is not None or self.is_auto


_AUTO_WORDS = frozenset(('auto', 'automatic', 'default'))


def parse_size_override(value):
    """Return a :class:`SizeOverride` for a stored queue value."""
    if value is None or isinstance(value, bool):
        return SizeOverride(None, False)
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return SizeOverride(None, False)
        if text in _AUTO_WORDS:
            return SizeOverride(None, True)
        # Accept the same forms as the size dialog: "24", "24G",
        # "24 GB", "24gb".
        text = text.replace(' ', '')
        for suffix in ('gb', 'g'):
            if text.endswith(suffix):
                text = text[:-len(suffix)]
                break
        try:
            number = float(text)
        except (TypeError, ValueError):
            return SizeOverride(None, False)
    elif isinstance(value, (int, float)):
        number = float(value)
    else:
        return SizeOverride(None, False)
    if not math.isfinite(number) or number <= 0:
        return SizeOverride(None, False)
    if number.is_integer():
        number = int(number)
    return SizeOverride(number, False)
