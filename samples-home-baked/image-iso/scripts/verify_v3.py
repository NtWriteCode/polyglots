#!/usr/bin/env python3
"""
verify_v3.py — JPEG + ISO 9660 polyglot verification harness.

Confirms the same bytes are read as JPEG by scanners and as ISO 9660 by
the OS / disc tools.
"""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pycdlib


def run(cmd: list[str], **kw) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"tool not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(cmd)}"


def check_libmagic_jpeg(path: Path) -> tuple[bool, str]:
    rc, out, _ = run(["file", "--brief", str(path)])
    out_lower = out.lower()
    ok = rc == 0 and "jpeg" in out_lower
    return ok, out.strip()


def check_jpeg_decodes(path: Path) -> tuple[bool, str]:
    """Confirm the JPEG face actually decodes to an image."""
    try:
        from PIL import Image
        with Image.open(path) as img:
            img.load()
            return True, f"{img.size[0]}x{img.size[1]} {img.mode}"
    except Exception as e:
        return False, f"decode failed: {e}"


def check_jpeg_soi(path: Path) -> tuple[bool, str]:
    with path.open("rb") as f:
        head = f.read(4)
    return (head[:3] == b"\xFF\xD8\xFF"), f"first 4 bytes = {head.hex()}"


def check_iso_pvd(path: Path) -> tuple[bool, str]:
    """ISO 9660 Primary Volume Descriptor at LBA 16 (offset 0x8000)."""
    with path.open("rb") as f:
        f.seek(0x8001)
        marker = f.read(5)
    return (marker == b"CD001"), f"marker at 0x8001 = {marker!r}"


def check_iso_listing(path: Path) -> tuple[bool, str]:
    """Re-open with pycdlib and list contents."""
    try:
        iso = pycdlib.PyCdlib()
        iso.open(str(path))
        names = []
        for child in iso.list_children(joliet_path="/"):
            n = child.file_identifier().decode("utf-16-be", errors="replace")
            if n not in (".", ".."):
                names.append(n)
        iso.close()
        ok = "payload.lnk" in names
        return ok, f"joliet entries: {names}"
    except Exception as e:
        return False, f"pycdlib open failed: {e}"


def check_lnk_extractable(path: Path) -> tuple[bool, str]:
    """Pull payload.lnk out of the ISO and confirm LNK signature."""
    try:
        iso = pycdlib.PyCdlib()
        iso.open(str(path))
        buf = io.BytesIO()
        iso.get_file_from_iso_fp(buf, joliet_path="/payload.lnk")
        iso.close()
        data = buf.getvalue()
    except Exception as e:
        return False, f"extract failed: {e}"
    if not data.startswith(b"\x4C\x00\x00\x00"):
        return False, f"extracted bytes don't start with LNK signature"
    return True, f"extracted {len(data)} bytes, LNK signature OK"


def check_extension_swap(path: Path) -> tuple[bool, str]:
    """Copy to .jpg, confirm libmagic + PIL still happy."""
    with tempfile.TemporaryDirectory() as td:
        as_jpg = Path(td) / "swap.jpg"
        shutil.copy(path, as_jpg)
        ok1, d1 = check_libmagic_jpeg(as_jpg)
        ok2, d2 = check_jpeg_decodes(as_jpg)
    return (ok1 and ok2), f"libmagic_jpeg={ok1} pil_decode={ok2}"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_v3.py <polyglot.iso>", file=sys.stderr)
        return 2
    target = Path(sys.argv[1])
    if not target.exists():
        print(f"not found: {target}", file=sys.stderr)
        return 2

    checks = [
        ("libmagic classifies as JPEG (cover)", check_libmagic_jpeg),
        ("JPEG SOI at offset 0",                check_jpeg_soi),
        ("JPEG decodes to an image (PIL)",      check_jpeg_decodes),
        ("ISO PVD 'CD001' at offset 0x8001",    check_iso_pvd),
        ("ISO listing via pycdlib",             check_iso_listing),
        ("payload.lnk extractable + valid LNK", check_lnk_extractable),
        (".jpg swap: libmagic + PIL OK",        check_extension_swap),
    ]

    print(f"verifying: {target} ({target.stat().st_size} bytes)\n")
    print(f"{'check':40} {'status':6}  detail")
    print(f"{'-'*40} {'-'*6}  {'-'*60}")
    all_ok = True
    for name, fn in checks:
        ok, detail = fn(target)
        all_ok &= ok
        print(f"{name:40} {'PASS' if ok else 'FAIL':6}  {detail}")
    print()
    print("RESULT:", "ALL PASS" if all_ok else "FAILURE")
    if all_ok:
        print()
        print("On Windows: rename to .iso, double-click → drive mounts,")
        print("payload.lnk visible → double-click runs calc.exe.")
        print("Same bytes also open as a JPEG in any image viewer.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
