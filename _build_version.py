"""Build-time version override (generated in CI, never edited by hand).

The release workflow overwrites this file with the version taken from the
pushed ``v*`` tag before PyInstaller runs.  The repository keeps ``None`` so
source runs fall back to ``APP_VERSION`` in ``exfat_builder.py``.
"""

BUILD_VERSION = None
