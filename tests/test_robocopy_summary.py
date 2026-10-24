"""Unit tests for robocopy_summary.py (localized summary parsing).

Run from the repo root:

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robocopy_summary import RobocopySummaryParser  # noqa: E402


ENGLISH = [
    '             Total    Copied   Skipped  Mismatch    FAILED    Extras',
    '    Dirs :     1343      1343         0         0         0         0',
    '   Files :    52655     52655         0         0         0         0',
    '   Bytes :  195.441 g 195.441 g         0         0         0         0',
    '   Times :   0:00:00   0:42:17   0:00:00   0:00:00',
]

FRENCH = [
    '             Total    Copié   Ignoré   ...',
    '    Dossiers :     1343      1343         0         0         0         0',
    '    Fichiers :    52655     52655         0         0         0         0',
    '      Octets :  195.441 g 195.441 g         0         0         0         0',
]

ITALIAN = [
    '             Totale   Copiati  Ignorati',
    '        Dir:     1343      1343         0         0         0         0',
    '       File:    52655     52655         0         0         0         0',
    '       Byte: 195441000 195441000         0         0         0         0',
]

GERMAN = [
    '             Gesamt  Kopiert  Übersprungen',
    '  Verzeichnisse:     1343      1343         0         0         0         0',
    '        Dateien:    52655     52655         0         0         0         0',
    '          Bytes: 195441000 195441000         0         0         0         0',
]

CHINESE = [
    '             总计    已复制   已跳过',
    '        目录:     1343      1343         0         0         0         0',
    '        文件:    52655     52655         0         0         0         0',
]

FULLWIDTH_COLON = [
    '        目录：     1343      1343         0         0         0         0',
    '        文件：    52655     52655         0         0         0         0',
]


def _feed_all(parser, lines):
    """Return [(line, result)] for each line."""
    return [(line, parser.feed(line)) for line in lines]


class RobocopySummaryParserTest(unittest.TestCase):

    def test_english_summary(self):
        parser = RobocopySummaryParser()
        results = _feed_all(parser, ENGLISH)
        self.assertEqual(results[1][1], None)       # Dirs
        self.assertEqual(results[2][1], 52655)      # Files
        self.assertEqual(results[3][1], None)       # Bytes
        self.assertEqual(results[4][1], None)       # Times
        self.assertEqual(parser.file_count, 52655)

    def test_localized_summaries(self):
        for lines in (FRENCH, ITALIAN, GERMAN, CHINESE,
                      FULLWIDTH_COLON):
            with self.subTest(lines=lines[1]):
                parser = RobocopySummaryParser()
                results = _feed_all(parser, lines)
                files = [value for _line, value in results
                         if value is not None]
                self.assertEqual(files, [52655])
                self.assertEqual(parser.file_count, 52655)

    def test_english_dirs_with_localized_files(self):
        parser = RobocopySummaryParser()
        parser.feed(ENGLISH[1])                     # English Dirs row
        self.assertEqual(parser.feed(FRENCH[2]), 52655)

    def test_localized_dirs_with_english_files(self):
        parser = RobocopySummaryParser()
        parser.feed(FRENCH[1])                      # Localized Dirs row
        self.assertEqual(parser.feed(ENGLISH[2]), 52655)

    def test_bytes_row_does_not_advance_row_counter(self):
        parser = RobocopySummaryParser()
        parser.feed(ENGLISH[1])                     # Dirs -> row 1
        parser.feed(ENGLISH[3])                     # Bytes -> ignored
        self.assertEqual(parser.rows_seen, 1)
        self.assertEqual(parser.feed(ENGLISH[2]), 52655)

    def test_non_summary_lines_are_ignored(self):
        parser = RobocopySummaryParser()
        for line in ('100%', '   71\tfile.bin',
                     'Options : /NFL /NDL /NP',
                     'Source : C:\\Games\\Some Game',
                     'Started : Tue Oct 21 12:00:00 2026',
                     '   Files : not numbers'):
            self.assertIsNone(parser.feed(line), line)
        self.assertEqual(parser.rows_seen, 0)

    def test_second_summary_is_not_reparsed_until_reset(self):
        parser = RobocopySummaryParser()
        _feed_all(parser, FRENCH)
        self.assertIsNone(parser.feed(FRENCH[1]))
        self.assertIsNone(parser.feed(FRENCH[2]))
        parser.reset()
        self.assertIsNone(parser.feed(FRENCH[1]))
        self.assertEqual(parser.feed(FRENCH[2]), 52655)

    def test_tab_separated_columns(self):
        parser = RobocopySummaryParser()
        parser.feed('Dossiers :\t1343\t1343\t0\t0\t0\t0')
        self.assertEqual(
            parser.feed('Fichiers :\t52655\t52655\t0\t0\t0\t0'),
            52655)

    def test_path_shaped_lines_are_ignored(self):
        parser = RobocopySummaryParser()
        self.assertIsNone(parser.feed(r'C:\Games\file: 1 2 3 4 5 6'))
        self.assertIsNone(parser.feed(r'New File: C:\x 1 2 3 4 5 6'))
        self.assertEqual(parser.rows_seen, 0)

    def test_ansi_codes_around_label(self):
        parser = RobocopySummaryParser()
        parser.feed('\x1b[36m    Dossiers :\x1b[0m  1343  1343  '
                    '0  0  0  0')
        self.assertEqual(
            parser.feed('\x1b[36m    Fichiers :\x1b[0m 52655 52655  '
                        '0  0  0  0'),
            52655)

    def test_empty_and_none(self):
        parser = RobocopySummaryParser()
        self.assertIsNone(parser.feed(''))
        self.assertIsNone(parser.feed(None))


if __name__ == '__main__':
    unittest.main()
