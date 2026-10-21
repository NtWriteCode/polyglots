#!/usr/bin/env python3
"""
build_polyglot.py — PE+ZIP polyglot stitcher (Variant 1: PE with ZIP overlay).

Pipeline:
  1. Read a compiled PE stub.
  2. Parse its headers (no external deps; only `struct`) and compute the
     end-of-last-section offset. Truncate the buffer there so any compiler
     padding / pre-existing overlay is dropped — our ZIP must start at a
     well-defined position.
  3. Append a ZIP archive built from a payload directory. zipfile's "a" mode
     on non-ZIP data writes offsets counted from the start of the file (like
     an SFX). A ZIP built separately and concatenated keeps offsets relative
     to its own start: lenient readers correct that, Windows Explorer
     rejects the file as invalid.
  4. Write the output.
  5. Self-check: re-parse the PE prefix and re-open the result with the
     stdlib `zipfile` module, calling testzip() to validate CRCs.

The script is stdlib-only and idempotent.
"""
from __future__ import annotations

import argparse
import io
import struct
import sys
import zipfile
from pathlib import Path


# --- PE structural parsing -------------------------------------------------

IMAGE_DOS_SIGNATURE = b"MZ"
IMAGE_NT_SIGNATURE = b"PE\x00\x00"

# COFF File Header: Machine, NumberOfSections, TimeDateStamp,
# PointerToSymbolTable, NumberOfSymbols, SizeOfOptionalHeader, Characteristics
COFF_HEADER_FMT = "<HHIIIHH"
COFF_HEADER_SIZE = struct.calcsize(COFF_HEADER_FMT)

# Section header (40 bytes): Name[8], VirtualSize, VirtualAddress,
# SizeOfRawData, PointerToRawData, PointerToRelocations,
# PointerToLinenumbers, NumberOfRelocations, NumberOfLinenumbers,
# Characteristics
SECTION_HEADER_FMT = "<8sIIIIIIHHI"
SECTION_HEADER_SIZE = struct.calcsize(SECTION_HEADER_FMT)
assert SECTION_HEADER_SIZE == 40


def pe_end_of_last_section(pe: bytes) -> int:
    """Return the file offset where the last PE section's raw data ends.

    Anything from this offset to EOF is the PE overlay — ignored by the
    Windows loader and therefore safe to replace with our ZIP payload.
    """
    if len(pe) < 64 or pe[:2] != IMAGE_DOS_SIGNATURE:
        raise ValueError("not a PE: missing MZ magic")

    e_lfanew = struct.unpack_from("<I", pe, 0x3C)[0]
    if e_lfanew + 4 > len(pe) or pe[e_lfanew:e_lfanew + 4] != IMAGE_NT_SIGNATURE:
        raise ValueError(f"not a PE: missing PE\\0\\0 at e_lfanew={e_lfanew:#x}")

    coff_off = e_lfanew + 4
    (_machine, n_sections, _tds, _psym, _nsym,
     size_opt_hdr, _chars) = struct.unpack_from(COFF_HEADER_FMT, pe, coff_off)

    sect_table_off = coff_off + COFF_HEADER_SIZE + size_opt_hdr
    if sect_table_off + n_sections * SECTION_HEADER_SIZE > len(pe):
        raise ValueError("PE truncated: section table exceeds file size")

    end = 0
    for i in range(n_sections):
        off = sect_table_off + i * SECTION_HEADER_SIZE
        (_name, _vsize, _vaddr, raw_size, raw_ptr,
         _prel, _plno, _nrel, _nlno, _ch) = struct.unpack_from(
            SECTION_HEADER_FMT, pe, off)
        # raw_ptr == 0 means uninitialized section with no file presence.
        if raw_ptr != 0:
            end = max(end, raw_ptr + raw_size)

    if end == 0 or end > len(pe):
        raise ValueError(f"PE section layout invalid: end={end} pe_len={len(pe)}")
    return end


# --- ZIP construction ------------------------------------------------------

def append_zip(prefix: bytes, payload_dir: Path) -> bytes:
    buf = io.BytesIO(prefix)
    buf.seek(0, io.SEEK_END)
    files = sorted(p for p in payload_dir.iterdir() if p.is_file())
    if not files:
        raise ValueError(f"no payload files in {payload_dir}")
    with zipfile.ZipFile(buf, mode="a", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.comment = b"PE+ZIP polyglot, Variant 1 (PE overlay)"
        for p in files:
            zf.write(p, arcname=p.name)
    return buf.getvalue()


# --- Orchestration ---------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pe", required=True, type=Path,
                    help="path to compiled PE stub (e.g. from mingw)")
    ap.add_argument("--payload", required=True, type=Path,
                    help="directory of files to include in the ZIP half")
    ap.add_argument("--out", required=True, type=Path,
                    help="output polyglot path")
    args = ap.parse_args()

    pe_raw = args.pe.read_bytes()
    end = pe_end_of_last_section(pe_raw)
    pe_core = pe_raw[:end]
    stripped = len(pe_raw) - end
    print(f"[pe]    {args.pe} : {len(pe_raw)} bytes, "
          f"end-of-last-section = {end:#x}, stripped overlay = {stripped} bytes")

    polyglot = append_zip(pe_core, args.payload)
    print(f"[zip]   appended {len(polyglot) - len(pe_core)} bytes from {args.payload}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(polyglot)
    print(f"[out]   wrote {args.out} : {len(polyglot)} bytes")

    # Self-check 1: PE prefix still parses.
    end2 = pe_end_of_last_section(polyglot)
    assert end2 == end, f"PE re-parse drift: {end2} != {end}"
    print(f"[check] PE prefix re-parses; end-of-last-section unchanged")

    # Self-check 2: ZIP half opens and CRCs validate.
    with zipfile.ZipFile(args.out) as zf:
        bad = zf.testzip()
        if bad is not None:
            print(f"[check] ZIP CRC failure on member: {bad}", file=sys.stderr)
            return 2
        names = zf.namelist()
    print(f"[check] ZIP testzip() OK, members = {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
