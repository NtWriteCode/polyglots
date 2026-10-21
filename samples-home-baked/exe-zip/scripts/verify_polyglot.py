#!/usr/bin/env python3
"""
verify_polyglot.py — multi-parser verification of a PE+ZIP polyglot.

Runs each independent check and prints a compatibility matrix. Exits 0 only
if every check passes.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def run(cmd: list[str], **kw) -> tuple[int, str, str]:
    """Run a command; return (rc, stdout, stderr). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kw)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"tool not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(cmd)}"


def check_pe_structure(path: Path) -> tuple[bool, str]:
    # Reuse the parser from build_polyglot.py without making it importable
    # by path-hacking — just re-implement the minimum here.
    import struct
    data = path.read_bytes()
    if data[:2] != b"MZ":
        return False, "missing MZ magic"
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return False, f"missing PE\\0\\0 at {e_lfanew:#x}"
    n_sections, _, _, _, size_opt_hdr, _ = struct.unpack_from(
        "<HIIIHH", data, e_lfanew + 4 + 2)
    return True, f"MZ + PE\\0\\0 OK, {n_sections} sections, opt_hdr={size_opt_hdr}"


def check_wine_runs(path: Path) -> tuple[bool, str]:
    rc, out, err = run(["wine", str(path)])
    ok = rc == 0 and "hello from polyglot" in out
    detail = f"rc={rc} stdout={out.strip()!r}"
    if err.strip() and not ok:
        detail += f" stderr={err.strip()[:120]!r}"
    return ok, detail


def check_python_zipfile(path: Path) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad is not None:
                return False, f"testzip() bad member: {bad}"
            return True, f"members={zf.namelist()} testzip=None"
    except zipfile.BadZipFile as e:
        return False, f"BadZipFile: {e}"


def check_unzip(path: Path) -> tuple[bool, str]:
    rc, out, err = run(["unzip", "-l", str(path)])
    # rc 0: offsets are absolute, so Info-ZIP has nothing to correct.
    ok = rc == 0 and "README.txt" in out
    return ok, f"rc={rc} listing_ok={'README.txt' in out}"


def check_7z(path: Path) -> tuple[bool, str]:
    rc, out, err = run(["7z", "l", str(path)])
    ok = rc == 0 and "README.txt" in out
    return ok, f"rc={rc} listing_ok={'README.txt' in out}"


def check_extension_swap(path: Path) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as td:
        zp = Path(td) / "polyglot.zip"
        shutil.copy(path, zp)
        results = [
            check_python_zipfile(zp),
            check_unzip(zp),
            check_7z(zp),
        ]
    failed = [d for ok, d in results if not ok]
    if failed:
        return False, "; ".join(failed)
    return True, "all three ZIP parsers accept the renamed file"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_polyglot.py <polyglot.exe>", file=sys.stderr)
        return 2
    target = Path(sys.argv[1])
    if not target.exists():
        print(f"not found: {target}", file=sys.stderr)
        return 2

    checks = [
        ("PE structural validity",  check_pe_structure),
        ("PE runs under wine",      check_wine_runs),
        ("ZIP — Python zipfile",    check_python_zipfile),
        ("ZIP — Info-ZIP unzip",    check_unzip),
        ("ZIP — 7-Zip",             check_7z),
        ("Extension-swap → .zip",   check_extension_swap),
    ]

    print(f"verifying: {target} ({target.stat().st_size} bytes)\n")
    print(f"{'check':32} {'status':6}  detail")
    print(f"{'-'*32} {'-'*6}  {'-'*40}")
    all_ok = True
    for name, fn in checks:
        ok, detail = fn(target)
        all_ok &= ok
        print(f"{name:32} {'PASS' if ok else 'FAIL':6}  {detail}")
    print()
    print("RESULT:", "ALL PASS" if all_ok else "FAILURE")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
