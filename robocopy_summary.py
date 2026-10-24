"""Locale-independent parsing of robocopy's end-of-run summary.

Robocopy translates the summary row labels (``Files :``, ``Fichiers :``,
``Dateien:``, ``文件:`` ...).  Matching the English word only means the
copy phase never sees its authoritative completion signal on non-English
Windows, which leaves the progress bar in the copy frame and makes the
build look stuck at ~99%.

The labels change; the numeric shape does not.  Each summary row is a
short label followed by six integer columns:

    Dossiers :     1343      1343         0         0         0         0
    Fichiers :    52655     52655         0         0         0         0
      Octets :  195.441 g 195.441 g         0         0         0         0
       Temps :   0:00:00   0:42:17 ...

Rows 1 and 2 are always Dirs and Files.  The Bytes row contains units and
the Times row contains clock values, so neither matches the six-integer
shape.
"""

from __future__ import annotations

import re

# Optional ANSI colour codes can wrap the label when a wrapper decorates
# robocopy output.  They are not expected in a redirected pipe, but
# stripping them costs nothing and keeps the numeric scan reliable.
_ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')

# A localized label followed by exactly six integer columns.  The label
# may contain spaces or non-ASCII letters; it may not contain digits, a
# colon, or a path separator (so paths such as "C:\..." cannot
# masquerade as a row).
_SUMMARY_ROW = re.compile(
    r'^\s*[^\d:：\\/\r\n]{1,40}?[:：]\s*'
    r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$')

# Fast path for English Windows; anchored and requiring the full
# six-column shape so a filename that happens to contain "Files : 12 34"
# cannot be mistaken for the summary.
_ENGLISH_FILES = re.compile(
    r'^\s*Files\s*[:：]\s*(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s*$')


class RobocopySummaryParser:
    """Track the Dirs and Files rows of a robocopy summary."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Forget rows from a previous robocopy run."""
        self.rows_seen = 0
        self.file_count = 0

    def feed(self, line):
        """Consume one output line.

        Returns the file total when *line* is the summary's Files row,
        otherwise ``None``.  The first six-integer row is Dirs and the
        second is Files, matching robocopy's fixed summary order.
        """
        if not line:
            return None
        text = _ANSI.sub('', line).strip()
        if not text:
            return None

        english = _ENGLISH_FILES.match(text)
        if english:
            self.rows_seen = 2
            self.file_count = int(english.group(1))
            return self.file_count

        match = _SUMMARY_ROW.match(text)
        if not match:
            return None
        if self.rows_seen >= 2:
            # A second summary in the same build (e.g. a retry) must not
            # be mistaken for the Files row; reset() starts a new build.
            return None
        self.rows_seen += 1
        if self.rows_seen != 2:
            return None
        self.file_count = int(match.group(1))
        return self.file_count
