#!/usr/bin/env python3
"""
verify_v4.py — JPEG + VHD polyglot verification harness.

Confirms scanners see JPEG, qemu sees a valid VHD, and the FAT16 partition
within carries the payload.lnk file.
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

SECTOR_SIZE = 512
VHD_FOOTER_SIZE = 512
PARTITION_START_OFFSET = 2048 * SECTOR_SIZE  # 0x100000


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


def check_jpeg_soi(path: Path) -> tuple[bool, str]:
    with path.open("rb") as f:
        head = f.read(4)
    return (head[:3] == b"\xFF\xD8\xFF"), f"first 4 bytes = {head.hex()}"


def check_mbr_signature(path: Path) -> tuple[bool, str]:
    with path.open("rb") as f:
        f.seek(0x1FE)
        sig = f.read(2)
    return (sig == b"\x55\xAA"), f"bytes [0x1FE:0x200] = {sig.hex()}"


def check_partition_table(path: Path) -> tuple[bool, str]:
    with path.open("rb") as f:
        f.seek(0x1BE)
        pte = f.read(16)
    ptype = pte[4]
    lba = struct.unpack_from("<I", pte, 8)[0]
    size = struct.unpack_from("<I", pte, 12)[0]
    ok = ptype == 0x0E and lba == 2048
    return ok, f"type=0x{ptype:02X} start_LBA={lba} size_sectors={size}"


def check_fat_boot_sector(path: Path) -> tuple[bool, str]:
    with path.open("rb") as f:
        f.seek(PARTITION_START_OFFSET)
        bs = f.read(64)
    jump_ok = bs[0] in (0xEB, 0xE9)
    sig_ok = False
    with path.open("rb") as f:
        f.seek(PARTITION_START_OFFSET + 510)
        bs_sig = f.read(2)
    sig_ok = bs_sig == b"\x55\xAA"
    oem = bs[3:11].decode("latin-1", errors="replace")
    return (jump_ok and sig_ok), \
        f"jump=0x{bs[0]:02X} OEM={oem!r} bs_sig={bs_sig.hex()}"


def check_vhd_footer(path: Path) -> tuple[bool, str]:
    size = path.stat().st_size
    with path.open("rb") as f:
        f.seek(size - VHD_FOOTER_SIZE)
        footer = f.read(VHD_FOOTER_SIZE)
    if footer[:8] != b"conectix":
        return False, f"cookie={footer[:8]!r}, not conectix"
    disk_type = struct.unpack_from(">I", footer, 60)[0]
    stored_cksum = struct.unpack_from(">I", footer, 64)[0]
    f_zeroed = bytearray(footer)
    f_zeroed[64:68] = b"\x00\x00\x00\x00"
    recomputed = (sum(f_zeroed) & 0xFFFFFFFF) ^ 0xFFFFFFFF
    cksum_ok = stored_cksum == recomputed
    return (disk_type == 2 and cksum_ok), \
        f"disk_type={disk_type} (2=fixed), checksum={stored_cksum:#010x} " \
        f"({'OK' if cksum_ok else 'BAD'})"


def check_qemu_img_autodetect_misses(path: Path) -> tuple[bool, str]:
    """qemu-img's auto-detector reads offset 0 and is fooled by the JPEG
    cover, classifying as 'raw' rather than 'vpc' (VHD). This is the
    cover working as intended — we WANT auto-detection to fail. We pass
    this check iff auto-detect does NOT classify as vpc/vhd, i.e. the
    cover defeats first-bytes typing."""
    rc, out, _ = run(["qemu-img", "info", str(path)])
    if rc != 0:
        return False, f"qemu-img rc={rc}"
    fmt_line = next((l for l in out.splitlines()
                     if "file format:" in l.lower()), "")
    fmt = fmt_line.split(":", 1)[-1].strip().lower() if fmt_line else ""
    # We want fmt to be 'raw' (i.e. auto-detect failed to recognize VHD).
    return (fmt != "vpc"), f"auto-detect format: {fmt!r} (cover defeats it)"


def check_qemu_img_forced_vpc(path: Path) -> tuple[bool, str]:
    """With -f vpc, qemu-img reads the footer and reports the correct
    virtual disk size (file size minus 512-byte footer)."""
    rc, out, _ = run(["qemu-img", "info", "-f", "vpc", str(path)])
    if rc != 0:
        return False, f"qemu-img -f vpc rc={rc}"
    # Look for 'virtual size:' line containing a bytes count.
    vsize_line = next((l for l in out.splitlines()
                       if "virtual size:" in l.lower()), "")
    expected_disk_size = path.stat().st_size - 512
    ok = str(expected_disk_size) in vsize_line
    return ok, vsize_line.strip() or "no virtual size line"


def check_lnk_in_partition(path: Path) -> tuple[bool, str]:
    """Extract the FAT region and read payload.lnk from it via pyfatfs."""
    from pyfatfs.PyFatFS import PyFatFS  # type: ignore

    size = path.stat().st_size
    fat_size = size - PARTITION_START_OFFSET - VHD_FOOTER_SIZE
    if fat_size <= 0:
        return False, "no FAT region between MBR pad and VHD footer"

    with tempfile.TemporaryDirectory() as td:
        fat_path = Path(td) / "extracted.fat"
        with path.open("rb") as fin, fat_path.open("wb") as fout:
            fin.seek(PARTITION_START_OFFSET)
            remaining = fat_size
            while remaining > 0:
                chunk = fin.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                fout.write(chunk)
                remaining -= len(chunk)
        try:
            fs = PyFatFS(str(fat_path))
            names = list(fs.listdir("/"))
            lnk_present = "payload.lnk" in names
            lnk_bytes = fs.readbytes("/payload.lnk") if lnk_present else b""
            fs.close()
        except Exception as e:
            return False, f"pyfatfs failed: {e}"
    sig_ok = lnk_bytes.startswith(b"\x4C\x00\x00\x00")
    return (lnk_present and sig_ok), \
        f"entries={names} lnk_bytes={len(lnk_bytes)} sig_ok={sig_ok}"


def check_extension_swap(path: Path) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as td:
        as_jpg = Path(td) / "swap.jpg"
        shutil.copy(path, as_jpg)
        rc, out, _ = run(["file", "--brief", str(as_jpg)])
    return ("jpeg" in out.lower()), out.strip()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_v4.py <polyglot.vhd>", file=sys.stderr)
        return 2
    target = Path(sys.argv[1])
    if not target.exists():
        print(f"not found: {target}", file=sys.stderr)
        return 2

    checks = [
        ("libmagic classifies as JPEG (cover)", check_libmagic_jpeg),
        ("JPEG SOI at offset 0",                check_jpeg_soi),
        ("MBR signature 55 AA at 0x1FE",        check_mbr_signature),
        ("MBR partition table sane",            check_partition_table),
        ("FAT boot sector at 0x100000",         check_fat_boot_sector),
        ("VHD footer ('conectix') + checksum",  check_vhd_footer),
        ("qemu-img auto-detect FOOLED (cover)", check_qemu_img_autodetect_misses),
        ("qemu-img -f vpc parses correctly",    check_qemu_img_forced_vpc),
        ("payload.lnk inside FAT16",            check_lnk_in_partition),
        (".jpg swap: libmagic still JPEG",      check_extension_swap),
    ]

    print(f"verifying: {target} ({target.stat().st_size} bytes)\n")
    print(f"{'check':40} {'status':6}  detail")
    print(f"{'-'*40} {'-'*6}  {'-'*72}")
    all_ok = True
    for name, fn in checks:
        ok, detail = fn(target)
        all_ok &= ok
        print(f"{name:40} {'PASS' if ok else 'FAIL':6}  {detail}")
    print()
    print("RESULT:", "ALL PASS" if all_ok else "FAILURE")
    if all_ok:
        print()
        print("On Windows: double-click the .vhd → Disk Management mounts it →")
        print("drive letter appears with payload.lnk → double-click → calc.exe.")
        print("Same bytes also open as a JPEG (very small image) in any viewer.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
