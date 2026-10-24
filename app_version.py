"""Resolve the application version for source and release builds.

Release builds embed ``_build_version.py``, generated from the pushed git
tag before PyInstaller runs.  Source runs (and builds without that file)
fall back to the ``APP_VERSION`` constant in ``exfat_builder.py``.
"""

from __future__ import annotations

import re

_VERSION_RE = re.compile(r'^\d+(?:\.\d+)*(?:[-+][0-9A-Za-z.-]+)?$')


def normalize_version(value):
    """Return a clean version string, or '' when *value* is unusable.

    Accepts a leading ``v``/``V`` so a git tag can be passed directly.
    """
    if value is None:
        return ''
    text = str(value).strip()
    if text[:1] in ('v', 'V'):
        text = text[1:].strip()
    return text if _VERSION_RE.match(text) else ''


def resolve_version(default, build_version=None):
    """Prefer the build-time (tag-derived) version, else *default*.

    The build override is ignored unless it looks like a version, so a
    corrupt or hand-edited ``_build_version.py`` cannot produce a bogus
    About/update-check version.
    """
    return normalize_version(build_version) or str(default).strip()
