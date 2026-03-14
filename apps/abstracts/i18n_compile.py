from __future__ import annotations

import re
import struct
from pathlib import Path
import gettext


_QUOTED_RE = re.compile(r'^"(.*)"$')


def _unquote(s: str) -> str:
    match = _QUOTED_RE.match(s.strip())
    if not match:
        return ""
    text = match.group(1)
    # Unescape the most common PO escapes while preserving Unicode characters.
    text = text.replace(r"\\n", "\n")
    text = text.replace(r"\\t", "\t")
    text = text.replace(r"\\r", "\r")
    text = text.replace(r'\\"', '"')
    text = text.replace(r"\\\\", "\\")
    return text


def compile_po_to_mo(po_path: Path, mo_path: Path) -> None:
    """
    Minimal .po -> .mo compiler (pure Python).
    Supports simple msgid/msgstr pairs (enough for our project strings).
    """
    messages: dict[str, str] = {}
    msgid: str | None = None
    msgstr: str | None = None
    in_msgid = False
    in_msgstr = False
    fuzzy = False

    for raw_line in po_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            if msgid is not None and msgstr is not None and not fuzzy:
                messages[msgid] = msgstr
            msgid = None
            msgstr = None
            in_msgid = False
            in_msgstr = False
            fuzzy = False
            continue

        if line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
            continue

        if line.startswith("msgid "):
            in_msgid = True
            in_msgstr = False
            msgid = _unquote(line[5:].strip())
            msgstr = ""
            continue

        if line.startswith("msgstr "):
            in_msgstr = True
            in_msgid = False
            msgstr = _unquote(line[6:].strip())
            continue

        if line.startswith('"'):
            if in_msgid and msgid is not None:
                msgid += _unquote(line)
            elif in_msgstr and msgstr is not None:
                msgstr += _unquote(line)

    if msgid is not None and msgstr is not None and not fuzzy:
        messages[msgid] = msgstr

    # The keys must be bytes-sorted.
    ids = sorted(messages.keys())
    id_bytes = b"\x00".join(s.encode("utf-8") for s in ids) + b"\x00"
    str_bytes = b"\x00".join(messages[s].encode("utf-8") for s in ids) + b"\x00"

    n = len(ids)
    # header is 7*4 bytes, then two tables with n entries of (len, offset)
    header_size = 7 * 4
    orig_table_offset = header_size
    trans_table_offset = orig_table_offset + n * 8
    orig_strings_offset = trans_table_offset + n * 8
    trans_strings_offset = orig_strings_offset + len(id_bytes)

    # Build offset tables
    offsets_orig: list[tuple[int, int]] = []
    offsets_trans: list[tuple[int, int]] = []

    current = 0
    for s in ids:
        b = s.encode("utf-8")
        offsets_orig.append((len(b), orig_strings_offset + current))
        current += len(b) + 1

    current = 0
    for s in ids:
        b = messages[s].encode("utf-8")
        offsets_trans.append((len(b), trans_strings_offset + current))
        current += len(b) + 1

    output = []
    output.append(struct.pack("<Iiiiiii", 0x950412DE, 0, n, orig_table_offset, trans_table_offset, 0, 0))
    for length, offset in offsets_orig:
        output.append(struct.pack("<II", length, offset))
    for length, offset in offsets_trans:
        output.append(struct.pack("<II", length, offset))
    output.append(id_bytes)
    output.append(str_bytes)

    mo_path.parent.mkdir(parents=True, exist_ok=True)
    mo_path.write_bytes(b"".join(output))


def compile_project_locales(locale_paths: list[str]) -> None:
    for base in locale_paths:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for po_path in base_path.glob("*/LC_MESSAGES/django.po"):
            mo_path = po_path.with_suffix(".mo")
            try:
                mo_is_valid = False
                if mo_path.exists():
                    try:
                        with mo_path.open("rb") as fp:
                            gettext.GNUTranslations(fp)
                        mo_is_valid = True
                    except Exception:
                        mo_is_valid = False

                if mo_is_valid and mo_path.stat().st_mtime >= po_path.stat().st_mtime:
                    continue
                compile_po_to_mo(po_path=po_path, mo_path=mo_path)
            except Exception:
                # Best-effort: if compilation fails, keep running with default strings.
                continue