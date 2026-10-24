"""Game metadata + output-filename naming for PS5 ExFAT Builder.

Pure-Python helpers with no Tkinter/Windows dependencies so they can be
unit-tested on any platform.  ``exfat_builder`` imports these functions,
and the UI imports them through ``exfat_builder`` for compatibility.

Version priority
----------------
1. ``sce_sys/pfs-version.dat`` -- the real installed patch version.
2. ``param.sfo`` ``VERSION`` / ``APP_VER``.
3. ``param.json`` ``version`` / ``masterVersion``.

Firmware priority
-----------------
1. ``param.json`` ``requiredSystemSoftwareVersion`` (exact required FW).
2. ``param.json`` ``systemVersion`` / ``SYSTEM_VER``.
3. ``param.sfo`` ``SYSTEM_VER`` / ``SDK_VER``.
"""

import json
import os
import re
import struct

__all__ = [
    'DEFAULT_OUTPUT_TEMPLATE',
    'CLASSIC_OUTPUT_TEMPLATE',
    'OUTPUT_TEMPLATE_PLACEHOLDERS',
    'parse_sfo',
    'find_meta_file',
    'find_sfo',
    'parse_param_json',
    'parse_nptitle_dat',
    'sanitize_filename',
    'normalize_version',
    'decode_ps5_firmware_value',
    'format_firmware',
    'get_game_metadata',
    'get_game_info',
    'render_output_stem',
    'output_template_unknown_placeholders',
    'build_exfat_name',
    'preview_output_name',
]

# Default output name.  The required firmware is appended only when the
# metadata provides it; empty placeholders have their brackets removed, so
# titles without a known firmware keep the historical
# "<TITLE_ID> <TITLE> (<VERSION>)" shape exactly.
DEFAULT_OUTPUT_TEMPLATE = '%PPSA% %TITLE% (%VERSION%) (%FIRMWARE%)'

# Pre-3.6.5 default, kept as a preset for users who do not want firmware
# in the filename.
CLASSIC_OUTPUT_TEMPLATE = '%PPSA% %TITLE% (%VERSION%)'

OUTPUT_TEMPLATE_PLACEHOLDERS = (
    ('%TITLE%', 'Game title'),
    ('%VERSION%', 'Game / patch version'),
    ('%FIRMWARE%', 'Required firmware (e.g. 12.70)'),
    ('%PPSA%', 'Title ID (e.g. PPSA01234)'),
    ('%TITLE_ID%', 'Alias for %PPSA%'),
    ('%TITLEID%', 'Alias for %PPSA%'),
    ('%ID%', 'Alias for %PPSA%'),
    ('%FW%', 'Alias for %FIRMWARE%'),
)

_TEMPLATE_ALIASES = {
    'TITLE': 'title',
    'VERSION': 'version',
    'FIRMWARE': 'firmware',
    'FW': 'firmware',
    'PPSA': 'title_id',
    'TITLE_ID': 'title_id',
    'TITLEID': 'title_id',
    'ID': 'title_id',
}

_PLACEHOLDER_RE = re.compile(r'%([A-Za-z0-9_]+)%')


# ── SFO / metadata readers ───────────────────────────────────────────────────

def parse_sfo(path):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) < 20:
            return {}
        magic, version, key_table_offset, data_table_offset, num_entries = \
            struct.unpack_from('<IIIII', data, 0)
        if magic != 0x46535000:
            return {}
        results = {}
        for i in range(num_entries):
            entry_offset = 20 + i * 16
            if entry_offset + 16 > len(data):
                break
            key_off, data_fmt, data_len, data_max_len, data_off = \
                struct.unpack_from('<HHIII', data, entry_offset)
            key_start = key_table_offset + key_off
            key_end   = data.index(b'\x00', key_start)
            key = data[key_start:key_end].decode('utf-8', errors='replace')
            val_start = data_table_offset + data_off
            if data_fmt == 0x0204:
                val = data[val_start:val_start+data_len].rstrip(b'\x00').decode('utf-8', errors='replace')
            elif data_fmt == 0x0404:
                val = struct.unpack_from('<I', data, val_start)[0]
            else:
                val = data[val_start:val_start+data_len]
            results[key] = val
        return results
    except Exception:
        return {}


def find_meta_file(folder, names):
    """Search for any of the given filenames within folder up to 5 levels deep."""
    folder = os.path.normpath(folder)
    # Fast-path: root and sce_sys
    for sub in ['', 'sce_sys']:
        for name in names:
            p = os.path.join(folder, sub, name) if sub else os.path.join(folder, name)
            if os.path.isfile(p):
                return p
    # Walk
    try:
        for root, dirs, files in os.walk(folder):
            rel = os.path.relpath(root, folder)
            depth = 0 if rel == '.' else rel.count(os.sep) + 1
            if depth > 5:
                dirs[:] = []
                continue
            lower_files = [f.lower() for f in files]
            for name in names:
                if name.lower() in lower_files:
                    idx = lower_files.index(name.lower())
                    return os.path.join(root, files[idx])
    except Exception:
        pass
    return None


def find_sfo(folder):
    return find_meta_file(folder, ['param.sfo'])


def parse_param_json(path):
    """Parse param.json used by some PS5 extraction tools instead of param.sfo."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
        title_id = data.get('titleId', '')
        version  = data.get('version') or data.get('masterVersion') or ''
        # Title is nested under localizedParameters
        title = ''
        lp = data.get('localizedParameters', {})
        if lp:
            default_lang = lp.get('defaultLanguage', 'en-US')
            for lang in [default_lang, 'en-US', 'en-GB']:
                t = lp.get(lang, {}).get('titleName', '')
                if t:
                    title = t
                    break
            if not title:
                # Try first available language
                for lang, val in lp.items():
                    if isinstance(val, dict) and val.get('titleName'):
                        title = val['titleName']
                        break
        # Some formats put title at top level
        if not title:
            title = data.get('titleName', '') or data.get('name', '')
        return title.strip(), str(title_id).strip(), str(version).strip()
    except Exception:
        return '', '', ''


def parse_nptitle_dat(path):
    """nptitle.dat is plain text containing just the game title on the first line."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.readline().strip()
    except Exception:
        return ''


def sanitize_filename(name):
    """Clean a game title so it's safe as a Windows filename, a cmd.exe
    argument, an exFAT volume label, and a PS5-readable filename.

    What we strip / replace:
      - Windows-reserved:  \\ / : * ? " < > |
      - cmd.exe metachars: & ^ % ! ` $          (cause "is not recognized"
                                                 errors when shell=True
                                                 builds — e.g. titles like
                                                 "Ratchet & Clank")
      - Curly/smart quotes: ' ' " " ´ `
                                          ‘ ’ “ ”
                                          → ASCII apostrophe / quote
      - Em/en/figure dashes: – — ― − → '-'
      - Trademark/copyright/registered/SM marks: ® © ™ ℠ → dropped
      - Bullets / interpuncts:  • · ‧ → space
      - Ellipsis … → '...'
      - C0/C1 control chars (anything < 0x20 or 0x7f-0x9f) → dropped
      - Collapse whitespace and strip leading/trailing dots and spaces
        (Windows silently strips trailing '.' and ' ' which corrupts
        downstream lookups).

    Length capped at 80 chars to stay well under exFAT's 255-char limit
    plus extension overhead.
    """
    if not name:
        return ''
    name = str(name)

    # ── Smart-quote / dash / mark normalisation FIRST so the
    # subsequent "drop" pass doesn't lose a meaningful character. ──
    _NORMALISE = {
        '‘': "'", '’': "'",                 # ' '
        '“': '"', '”': '"',                 # " "
        '´': "'", '`': "'",                 # ´ `
        '–': '-', '—': '-',                 # – —
        '―': '-', '−': '-',                 # ― −
        '…': '...',                               # …
        '•': ' ', '·': ' ', '‧': ' ',  # • · ‧
        '®': '',  '©': '',                  # ® ©
        '™': '',  '℠': '',                  # ™ ℠
    }
    for src, dst in _NORMALISE.items():
        if src in name:
            name = name.replace(src, dst)

    # ── Drop control chars (NUL, BEL, etc) and DEL ──
    name = ''.join(ch for ch in name
                   if ch == '\t' or (0x20 <= ord(ch) < 0x7f) or ord(ch) > 0x9f)

    # ── Strip Windows-reserved + cmd.exe metacharacters ──
    # The cmd.exe set is the critical fix: titles like "Ratchet & Clank"
    # currently cause `shell=True` to split the command at the &.
    name = re.sub(r'[\\/:*?"<>|&^%!`$]', '', name)

    # ── Collapse runs of whitespace, then trim leading/trailing dots
    # and spaces (Windows silently strips trailing ones, which would
    # break later lookups by exact name). ──
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.strip(' .')

    # ── Final safety: cap length, and never return an empty string ──
    name = name[:80]
    return name or 'game'


# ── Version / firmware normalisation ────────────────────────────────────────

def normalize_version(version):
    """Normalise to the consistent XX.XXX.XXX shape.

    ``"01.00"`` -> ``"01.000.000"``; ``"01.00.000"`` -> ``"01.000.000"``;
    ``"01.000.000"`` unchanged.  Values that are not dotted numeric
    strings are returned stripped and untouched.
    """
    if version is None:
        return None
    if not isinstance(version, str):
        version = str(version)
    version = version.strip()
    if not version:
        return None
    parts = version.split('.')
    if len(parts) == 2:
        parts.append('000')
    if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
        parts[0] = parts[0].zfill(2)
        parts[1] = parts[1].zfill(3)
        parts[2] = parts[2].zfill(3)
        version = '.'.join(parts[:3])
    return version


def _bcd_major_minor(digits):
    """Interpret the first four hex characters as packed BCD digits."""
    if len(digits) < 2:
        return None
    major_str = digits[:2]
    minor_str = digits[2:4] if len(digits) >= 4 else '00'
    if not (major_str.isdigit() and minor_str.isdigit()):
        return None
    major, minor = int(major_str), int(minor_str)
    if 1 <= major <= 30:
        return (major, minor)
    return None


def decode_ps5_firmware_value(raw):
    """Decode a PS5 firmware/SDK version field into ``(major, minor)``.

    PS5 ``param.json`` stores these as a packed quad-word where the hex
    CHARACTERS are the printed version digits (BCD), e.g.
    ``0x1270000000000000`` -> ``(12, 70)`` (FW 12.70) and
    ``0x1000000000000000`` -> ``(10, 0)``.

    Also accepts already-decoded strings such as ``"12.70"``, plain
    integers (``12``) and 32-bit SFO values (``0x09000000``).
    Returns ``None`` when the value cannot be understood.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None

    if isinstance(raw, int):
        # Packed BCD stored as a number, e.g. 0x12700000.
        if raw <= 0:
            return None
        hex_digits = format(raw, 'X')
        packed = _bcd_major_minor(hex_digits)
        if packed:
            return packed
        # SFO style 0x09000000 — top byte is the major.
        if raw > 0xFF:
            major = (raw >> 24) & 0xFF
            if 1 <= major <= 30:
                return (major, 0)
        if 0 <= raw <= 30:
            return (raw, 0)
        return None

    s = str(raw).strip()
    if not s:
        return None

    # Dotted form, e.g. "12.70" / "12.7".
    dotted = re.fullmatch(r'(\d{1,2})\.(\d{1,3})', s)
    if dotted:
        major, minor = int(dotted.group(1)), int(dotted.group(2))
        # PS5 firmware minors are two-digit ("12.70", "10.01").  A
        # one-digit form is shorthand for the tens: "12.7" -> 12.70.
        if len(dotted.group(2)) == 1:
            minor *= 10
        return (major, minor) if 1 <= major <= 30 else None

    if s.lower().startswith('0x'):
        digits = s[2:].replace('_', '').replace('-', '').replace(' ', '')
        if len(digits) < 2:
            return None
        packed = _bcd_major_minor(digits)
        if packed:
            return packed
        try:
            value = int(digits, 16)
        except ValueError:
            return None
        # Hex chars contained a-f: not BCD; use the top byte.
        nbits = len(digits) * 4
        if nbits >= 16:
            shift = nbits - 8
            major = (value >> shift) & 0xFF
        else:
            major = value & 0xFF
        return (major, 0) if 1 <= major <= 30 else None

    # Plain digits, e.g. "12".
    if s.isdigit():
        major = int(s)
        return (major, 0) if 1 <= major <= 30 else None
    return None


def format_firmware(major_minor):
    """Format ``(major, minor)`` as ``"12.70"`` / ``"10.00"``, or ``None``."""
    if not major_minor:
        return None
    try:
        major, minor = int(major_minor[0]), int(major_minor[1] or 0)
    except (TypeError, ValueError, IndexError):
        return None
    if not 1 <= major <= 30:
        return None
    return '%d.%02d' % (major, minor)


# ── Combined metadata ───────────────────────────────────────────────────────

def _read_param_json_fields(folder):
    """Return (title, title_id, version, firmware_value, path) from param.json."""
    json_path = find_meta_file(folder, ['param.json'])
    if not json_path:
        return ('', '', '', None, None)
    title, title_id, version = parse_param_json(json_path)
    fw_raw = None
    try:
        with open(json_path, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)
        for key in ('requiredSystemSoftwareVersion', 'systemVersion', 'SYSTEM_VER'):
            if data.get(key) is not None:
                fw_raw = data.get(key)
                break
    except Exception:
        pass
    return (title, title_id, version, fw_raw, json_path)


def get_game_metadata(folder):
    """Read all naming-relevant metadata for a game folder.

    Returns a dict with keys ``title``, ``title_id``, ``version``,
    ``firmware`` (formatted, e.g. ``"12.70"``), ``version_source``,
    ``firmware_source`` and ``pfs_version``.  Missing values are ``None``.
    """
    folder = os.path.normpath(folder)
    title, title_id, version = '', '', ''
    version_source = None
    firmware_raw = None
    firmware_source = None
    pfs_version = None

    # ── param.sfo ──
    sfo_path = find_sfo(folder)
    if sfo_path:
        info = parse_sfo(sfo_path)
        if info:
            title    = info.get('TITLE') or info.get('TITLE_00') or ''
            title_id = info.get('TITLE_ID', '')
            version  = info.get('VERSION') or info.get('APP_VER') or ''
            if isinstance(title_id, int):
                title_id = ''
            if version:
                version_source = 'param.sfo'
            for key in ('SYSTEM_VER', 'SDK_VER', 'SYSTEM_VERSION'):
                if info.get(key) is not None:
                    firmware_raw = info.get(key)
                    firmware_source = 'param.sfo'
                    break
    sfo_version = version

    # ── pfs-version.dat — highest priority for version ──
    pfs_path = find_meta_file(folder, ['pfs-version.dat'])
    if pfs_path:
        try:
            with open(pfs_path, 'r', encoding='utf-8', errors='replace') as f:
                pfs_ver = f.read().strip().split('\n')[0].strip()
            if pfs_ver and re.match(r'[\d.]+', pfs_ver):
                pfs_version = pfs_ver
                version = pfs_ver
                version_source = 'pfs-version.dat'
        except Exception:
            pass

    # ── param.json (always read: it is the authoritative firmware source) ──
    j_title, j_id, j_version, j_fw, j_path = _read_param_json_fields(folder)
    if not title and not title_id:
        title    = title or j_title
        title_id = title_id or j_id
        if not sfo_version and not version and j_version:
            version = j_version
            version_source = 'param.json'
    if j_fw is not None:
        firmware_raw = j_fw
        firmware_source = 'param.json'

    # ── nptitle.dat fallback for the title only ──
    if not title:
        npt_path = find_meta_file(folder, ['nptitle.dat'])
        if npt_path:
            title = parse_nptitle_dat(npt_path)

    normalized_version = normalize_version(version)
    firmware = format_firmware(decode_ps5_firmware_value(firmware_raw))

    return {
        'title': sanitize_filename(str(title)) if title else None,
        'title_id': str(title_id).strip() if title_id else None,
        'version': normalized_version,
        'firmware': firmware,
        'version_source': version_source if normalized_version else None,
        'firmware_source': firmware_source if firmware else None,
        'pfs_version': pfs_version,
    }


def get_game_info(folder):
    """Backward-compatible ``(title, title_id, version)`` tuple."""
    meta = get_game_metadata(folder)
    return (meta['title'], meta['title_id'], meta['version'])


# ── Output template rendering ───────────────────────────────────────────────

def output_template_unknown_placeholders(template):
    """Return the sorted unknown ``%TOKEN%`` names in *template*."""
    if not template:
        return []
    unknown = []
    for token in _PLACEHOLDER_RE.findall(template):
        if token.upper() not in _TEMPLATE_ALIASES:
            unknown.append(token)
    return sorted({t for t in unknown})


def _clean_rendered(text):
    """Tidy separators left behind by empty placeholders."""
    if not text:
        return ''
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r'\(\s*\)|\[\s*\]|\{\s*\}', '', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\s+([,;)\]])', r'\1', text)
    text = re.sub(r'([(\[])\s+', r'\1', text)
    text = text.strip(' ._-')
    return text


def render_output_stem(title, title_id, version, firmware=None, template=None):
    """Render a filename stem (no extension) from *template*.

    Unknown placeholders are left untouched so the UI can flag them.
    Empty values remove their surrounding bracket pair, e.g.
    ``%TITLE% (%VERSION%)`` with no version renders as just the title.
    """
    template = template if template else DEFAULT_OUTPUT_TEMPLATE
    values = {
        'title': title or '',
        'title_id': title_id or '',
        'version': version or '',
        'firmware': firmware or '',
    }
    # A folder whose title equals its ID should not repeat it.
    if values['title'] and values['title'].strip().upper() == values['title_id'].strip().upper():
        values['title'] = ''

    def _sub(match):
        key = _TEMPLATE_ALIASES.get(match.group(1).upper())
        if key is None:
            return match.group(0)
        return values.get(key, '')

    rendered = _PLACEHOLDER_RE.sub(_sub, str(template))
    return _clean_rendered(rendered)


def build_exfat_name(title, title_id, version, firmware=None, template=None,
                     ext='.exfat'):
    """Build an output filename using *template*.

    The default is ``"PPSA01234 Game Title (01.000.000) (10.00).exfat"``;
    ``CLASSIC_OUTPUT_TEMPLATE`` reproduces the historical
    ``"PPSA01234 Game Title (01.000.000).exfat"`` shape without firmware.
    """
    if not title and not title_id:
        stem = ''
    else:
        stem = render_output_stem(title, title_id, version, firmware, template)
    stem = sanitize_filename(stem) if stem else ''
    if not stem:
        stem = 'game'
    if not ext:
        ext = ''
    elif not str(ext).startswith('.'):
        ext = '.' + str(ext)
    return stem + ext


def preview_output_name(template=None, ext='.exfat'):
    """Return a ready-to-show preview for the settings UI."""
    return build_exfat_name(
        "Marvel's Spider-Man 2", 'PPSA01234', '01.000.000', '10.00',
        template=template, ext=ext)


if __name__ == '__main__':  # pragma: no cover - manual smoke test
    print(get_game_metadata('.'))
    print(preview_output_name())
    print(preview_output_name('%TITLE% (%VERSION%) (%FIRMWARE%) (%PPSA%)'))
