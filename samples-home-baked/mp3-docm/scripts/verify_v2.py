#!/usr/bin/env python3
"""
verify_v2.py — multi-tool verification of an MP3+DOCM polyglot.

Confirms the central research claim: same bytes, two verdicts.

Note on LibreOffice: it identifies the file by its first bytes (the MP3) and
refuses to load it, with or without patched offsets. The demo uses Word on
Windows. Word needs the absolute offsets checked below: with SFX-style
relative offsets it reports the package as corrupt and offers a repair.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def run(cmd: list[str], **kw) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"tool not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(cmd)}"


def check_libmagic_audio(path: Path) -> tuple[bool, str]:
    """The headline talk claim: scanners using libmagic classify as audio."""
    rc, out, _ = run(["file", "--brief", str(path)])
    out_lower = out.lower()
    ok = rc == 0 and any(k in out_lower for k in ("audio", "mp3", "id3"))
    return ok, out.strip()


def check_id3v2_at_offset_zero(path: Path) -> tuple[bool, str]:
    with path.open("rb") as f:
        head = f.read(10)
    if head[:3] != b"ID3":
        return False, f"first 3 bytes = {head[:3]!r}, not 'ID3'"
    return True, f"ID3v2 v{head[3]}.{head[4]} at offset 0"


def check_ffprobe_audio(path: Path) -> tuple[bool, str]:
    """Confirm the MP3 face is structurally valid as audio."""
    rc, out, _ = run(["ffprobe", "-v", "error", "-show_streams", str(path)])
    audio = "codec_type=audio" in out
    return (rc == 0 and audio), f"rc={rc} audio_stream_found={audio}"


def check_zip_office_parts(path: Path) -> tuple[bool, str]:
    """The DOCM face: ZIP integrity + presence of required OOXML parts."""
    try:
        with zipfile.ZipFile(path) as zf:
            bad = zf.testzip()
            if bad is not None:
                return False, f"bad ZIP member: {bad}"
            names = zf.namelist()
    except zipfile.BadZipFile as e:
        return False, f"BadZipFile: {e}"
    needed = ["[Content_Types].xml", "_rels/.rels", "word/document.xml"]
    missing = [n for n in needed if n not in names]
    if missing:
        return False, f"missing Office parts: {missing}"
    has_vba = "word/vbaProject.bin" in names
    return True, f"{len(names)} members, vbaProject.bin: {has_vba}"


def check_zip_offsets_absolute(path: Path) -> tuple[bool, str]:
    """Strict parsers (Word): every CD entry must point straight at its local header."""
    data = path.read_bytes()
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
    # zipfile adds the prepended length (concat) to header_offset; strict parsers do not.
    eocd = data.rfind(b"PK\x05\x06")
    cd_size, cd_off = int.from_bytes(data[eocd + 12:eocd + 16], "little"), int.from_bytes(data[eocd + 16:eocd + 20], "little")
    concat = eocd - cd_size - cd_off
    bad = [i.filename for i in infos if data[i.header_offset - concat:i.header_offset - concat + 4] != b"PK\x03\x04"]
    return (concat == 0 and not bad), f"prepended-length correction needed: {concat} bytes, wrong offsets: {len(bad)}"


def check_vba_macro_present(path: Path) -> tuple[bool, str]:
    """The macro carrier face: vbaProject.bin is non-empty OLE compound."""
    try:
        with zipfile.ZipFile(path) as zf:
            if "word/vbaProject.bin" not in zf.namelist():
                return False, "no word/vbaProject.bin"
            vba = zf.read("word/vbaProject.bin")
    except Exception as e:
        return False, f"read error: {e}"
    # OLE compound file magic: D0 CF 11 E0 A1 B1 1A E1
    OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
    if not vba.startswith(OLE_MAGIC):
        return False, f"vbaProject.bin not an OLE compound file (first 8 = {vba[:8].hex()})"
    return True, f"OLE compound file, {len(vba)} bytes"


def check_extension_swap_audio(path: Path) -> tuple[bool, str]:
    """Same bytes, .mp3 extension — libmagic + ffprobe both happy."""
    with tempfile.TemporaryDirectory() as td:
        as_mp3 = Path(td) / "swap.mp3"
        shutil.copy(path, as_mp3)
        ok1, detail1 = check_libmagic_audio(as_mp3)
        ok2, detail2 = check_ffprobe_audio(as_mp3)
    return (ok1 and ok2), f"libmagic_audio={ok1} ffprobe_audio={ok2}"


def check_extension_swap_zip(path: Path) -> tuple[bool, str]:
    """Same bytes, .docm extension — every lenient ZIP parser opens it."""
    with tempfile.TemporaryDirectory() as td:
        as_docm = Path(td) / "swap.docm"
        shutil.copy(path, as_docm)
        # Python zipfile
        ok_py, detail_py = check_zip_office_parts(as_docm)
        # Info-ZIP unzip
        rc, out, _ = run(["unzip", "-l", str(as_docm)])
        ok_unzip = rc in (0, 1) and "word/document.xml" in out
        # 7-Zip
        rc7, out7, _ = run(["7z", "l", str(as_docm)])
        ok_7z = rc7 == 0 and "word/document.xml" in out7
    return (ok_py and ok_unzip and ok_7z), \
        f"py={ok_py} unzip={ok_unzip} 7z={ok_7z}"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_v2.py <polyglot.docm>", file=sys.stderr)
        return 2
    target = Path(sys.argv[1])
    if not target.exists():
        print(f"not found: {target}", file=sys.stderr)
        return 2

    checks = [
        ("libmagic classifies as AUDIO (cover)", check_libmagic_audio),
        ("ID3v2 header at offset 0",             check_id3v2_at_offset_zero),
        ("ffprobe accepts as audio",             check_ffprobe_audio),
        ("ZIP + required Office parts",          check_zip_office_parts),
        ("ZIP offsets absolute (Word)",          check_zip_offsets_absolute),
        ("VBA macro present (OLE bin)",          check_vba_macro_present),
        (".mp3 swap: libmagic+ffprobe audio",    check_extension_swap_audio),
        (".docm swap: py/unzip/7z all open",     check_extension_swap_zip),
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
        print("Known parser divergence (not a failure, a research finding):")
        print("  - Microsoft Word: ACCEPTS  (test on Windows VM at demo time)")
        print("  - LibreOffice:    REJECTS  (insists ZIP at offset 0)")
        print("  - This divergence is itself talk-worthy material.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
