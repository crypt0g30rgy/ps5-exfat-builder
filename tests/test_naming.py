"""Unit tests for naming.py (metadata, firmware decoding, output templates).

Run from the repo root:

    python -m unittest discover -s tests -v

The module is pure Python, so these tests run on Linux even though the GUI
is Windows-only.
"""

from __future__ import annotations

import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import naming  # noqa: E402


def _make_sfo(entries):
    """Build a minimal valid PSF/param.sfo from (key, fmt, raw_bytes)."""
    key_blob = b''
    key_offsets = []
    for key, _fmt, _raw in entries:
        key_offsets.append(len(key_blob))
        key_blob += key.encode('ascii') + b'\x00'

    data_blob = b''
    data_offsets = []
    for _key, _fmt, raw in entries:
        data_offsets.append(len(data_blob))
        data_blob += raw
        padding = (-len(data_blob)) % 4
        data_blob += b'\x00' * padding

    key_table_offset = 20 + 16 * len(entries)
    data_table_offset = key_table_offset + len(key_blob)

    header = struct.pack('<IIIII', 0x46535000, 0x101,
                         key_table_offset, data_table_offset, len(entries))
    index = b''
    for (key, fmt, raw), key_off, data_off in zip(
            entries, key_offsets, data_offsets):
        index += struct.pack('<HHIII', key_off, fmt, len(raw), len(raw),
                             data_off)
    return header + index + key_blob + data_blob


class FirmwareDecodeTests(unittest.TestCase):
    def test_packed_bcd_string(self):
        self.assertEqual(
            naming.decode_ps5_firmware_value('0x1270000000000000'), (12, 70))
        self.assertEqual(
            naming.decode_ps5_firmware_value('0x1000000000000000'), (10, 0))
        self.assertEqual(
            naming.decode_ps5_firmware_value('0x1700000000000000'), (17, 0))

    def test_packed_bcd_integer(self):
        self.assertEqual(
            naming.decode_ps5_firmware_value(0x12700000), (12, 70))

    def test_sfo_style_top_byte(self):
        self.assertEqual(naming.decode_ps5_firmware_value(0x09000000), (9, 0))
        self.assertEqual(naming.decode_ps5_firmware_value('0x09000000'), (9, 0))

    def test_dotted_and_plain(self):
        self.assertEqual(naming.decode_ps5_firmware_value('12.70'), (12, 70))
        self.assertEqual(naming.decode_ps5_firmware_value('12.7'), (12, 70))
        self.assertEqual(naming.decode_ps5_firmware_value(12), (12, 0))

    def test_invalid(self):
        for raw in (None, '', 'nonsense', 0, -1, 99, '99.00'):
            self.assertIsNone(naming.decode_ps5_firmware_value(raw), raw)

    def test_format(self):
        self.assertEqual(naming.format_firmware((12, 70)), '12.70')
        self.assertEqual(naming.format_firmware((10, 0)), '10.00')
        self.assertIsNone(naming.format_firmware(None))


class VersionTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(naming.normalize_version('01.00'), '01.000.000')
        self.assertEqual(naming.normalize_version('01.00.000'), '01.000.000')
        self.assertEqual(naming.normalize_version('01.000.000'), '01.000.000')
        self.assertEqual(naming.normalize_version('1.007.000'), '01.007.000')
        self.assertIsNone(naming.normalize_version(''))
        self.assertIsNone(naming.normalize_version(None))


class OutputTemplateTests(unittest.TestCase):
    def test_default_includes_required_firmware(self):
        self.assertEqual(
            naming.build_exfat_name("Marvel's Spider-Man 2", 'PPSA01234',
                                    '01.000.000', '10.00'),
            "PPSA01234 Marvel's Spider-Man 2 (01.000.000) (10.00).exfat")

    def test_default_without_firmware_keeps_classic_shape(self):
        self.assertEqual(
            naming.build_exfat_name("Marvel's Spider-Man 2", 'PPSA01234',
                                    '01.000.000'),
            "PPSA01234 Marvel's Spider-Man 2 (01.000.000).exfat")

    def test_classic_template_preserves_historical_name(self):
        self.assertEqual(
            naming.build_exfat_name(
                "Marvel's Spider-Man 2", 'PPSA01234', '01.000.000', '10.00',
                template=naming.CLASSIC_OUTPUT_TEMPLATE),
            "PPSA01234 Marvel's Spider-Man 2 (01.000.000).exfat")

    def test_preview_matches_default_template(self):
        self.assertEqual(
            naming.preview_output_name(),
            "PPSA01234 Marvel's Spider-Man 2 (01.000.000) (10.00).exfat")

    def test_default_omits_missing_version(self):
        self.assertEqual(naming.build_exfat_name('Some Game', 'PPSA00001', None),
                         'PPSA00001 Some Game.exfat')

    def test_user_template_with_firmware(self):
        self.assertEqual(
            naming.build_exfat_name(
                "Marvel's Spider-Man 2", 'PPSA01234', '01.000.000', '10.00',
                '%TITLE% (%VERSION%) (%FIRMWARE%) (%PPSA%)'),
            "Marvel's Spider-Man 2 (01.000.000) (10.00) (PPSA01234).exfat")

    def test_missing_values_remove_brackets(self):
        self.assertEqual(
            naming.build_exfat_name('Some Game', None, None, None,
                                    '%TITLE% (%VERSION%) (%FIRMWARE%) (%PPSA%)'),
            'Some Game.exfat')

    def test_title_equal_to_id_not_duplicated(self):
        self.assertEqual(
            naming.build_exfat_name('PPSA01234', 'PPSA01234', '01.000.000',
                                    template='%PPSA% %TITLE% (%VERSION%)'),
            'PPSA01234 (01.000.000).exfat')

    def test_custom_extension(self):
        self.assertTrue(naming.build_exfat_name(
            'Game', 'PPSA00001', None, ext='.ffpkg').endswith('.ffpkg'))

    def test_sanitization_applies_after_template(self):
        name = naming.build_exfat_name(
            'Ratchet: Rift & Clank', 'PPSA00002', '01.000.000')
        self.assertNotIn(':', name)
        self.assertNotIn('&', name)

    def test_unknown_placeholders_reported_and_left_alone(self):
        self.assertEqual(
            naming.output_template_unknown_placeholders('%TITLE% %BOGUS%'),
            ['BOGUS'])
        self.assertEqual(
            naming.render_output_stem('Game', 'PPSA00001', None,
                                      template='%TITLE% %BOGUS%'),
            'Game %BOGUS%')


class MetadataTests(unittest.TestCase):
    def test_sfo_metadata_and_param_json_firmware(self):
        with tempfile.TemporaryDirectory() as tmp:
            sce = os.path.join(tmp, 'sce_sys')
            os.makedirs(sce)
            sfo = _make_sfo([
                ('TITLE', 0x0204, b'Test Game\x00'),
                ('TITLE_ID', 0x0204, b'PPSA01234\x00'),
                ('APP_VER', 0x0204, b'01.00\x00'),
                ('SYSTEM_VER', 0x0404,
                 struct.pack('<I', 0x09000000)),
            ])
            with open(os.path.join(sce, 'param.sfo'), 'wb') as fh:
                fh.write(sfo)
            with open(os.path.join(sce, 'param.json'), 'w',
                      encoding='utf-8') as fh:
                json.dump({
                    'titleId': 'PPSA01234',
                    'localizedParameters': {
                        'en-US': {'titleName': 'Test Game'}},
                    'requiredSystemSoftwareVersion': '0x1000000000000000',
                }, fh)

            meta = naming.get_game_metadata(tmp)
            self.assertEqual(meta['title'], 'Test Game')
            self.assertEqual(meta['title_id'], 'PPSA01234')
            self.assertEqual(meta['version'], '01.000.000')
            self.assertEqual(meta['version_source'], 'param.sfo')
            self.assertEqual(meta['firmware'], '10.00')
            self.assertEqual(meta['firmware_source'], 'param.json')
            self.assertEqual(naming.get_game_info(tmp),
                             ('Test Game', 'PPSA01234', '01.000.000'))

    def test_pfs_version_overrides_sfo(self):
        with tempfile.TemporaryDirectory() as tmp:
            sce = os.path.join(tmp, 'sce_sys')
            os.makedirs(sce)
            sfo = _make_sfo([
                ('TITLE', 0x0204, b'Test Game\x00'),
                ('TITLE_ID', 0x0204, b'PPSA01234\x00'),
                ('APP_VER', 0x0204, b'01.00\x00'),
            ])
            with open(os.path.join(sce, 'param.sfo'), 'wb') as fh:
                fh.write(sfo)
            with open(os.path.join(sce, 'pfs-version.dat'), 'w',
                      encoding='utf-8') as fh:
                fh.write('01.007.000\n')

            meta = naming.get_game_metadata(tmp)
            self.assertEqual(meta['version'], '01.007.000')
            self.assertEqual(meta['version_source'], 'pfs-version.dat')
            self.assertEqual(meta['pfs_version'], '01.007.000')

    def test_param_json_only_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, 'param.json'), 'w',
                      encoding='utf-8') as fh:
                json.dump({
                    'titleId': 'PPSA09999',
                    'version': '01.002.000',
                    'localizedParameters': {
                        'defaultLanguage': 'en-US',
                        'en-US': {'titleName': 'JSON Only'}},
                    'requiredSystemSoftwareVersion': '0x1270000000000000',
                }, fh)

            meta = naming.get_game_metadata(tmp)
            self.assertEqual(meta['title'], 'JSON Only')
            self.assertEqual(meta['title_id'], 'PPSA09999')
            self.assertEqual(meta['version'], '01.002.000')
            self.assertEqual(meta['version_source'], 'param.json')
            self.assertEqual(meta['firmware'], '12.70')

    def test_missing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = naming.get_game_metadata(tmp)
            self.assertIsNone(meta['title'])
            self.assertIsNone(meta['title_id'])
            self.assertIsNone(meta['version'])
            self.assertIsNone(meta['firmware'])
            self.assertEqual(naming.get_game_info(tmp), (None, None, None))


if __name__ == '__main__':
    unittest.main()
