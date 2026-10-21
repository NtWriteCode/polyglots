#!/usr/bin/env python3
"""
build_v4.py — JPEG + VHD (mountable disk) polyglot.

Layout:
  offset 0x000  ─┐
                 │ JPEG bytes (≤ 446 bytes)
                 │  → libmagic reads here, says "JPEG image data"
  offset 0x1BE  ─┤
                 │ MBR partition table (1 entry, FAT16-LBA, start LBA 2048)
  offset 0x1FE  ─┤
                 │ MBR signature 55 AA
  offset 0x200  ─┤
                 │ Zero-pad to LBA 2048 (= offset 0x100000)
  offset 0x100000┤
                 │ FAT16 partition image (mkfs.fat output, contains payload.lnk)
                 │
  EOF-512       ─┤
                 │ VHD fixed footer ("conectix")
  EOF           ─┘
"""
from __future__ import annotations

import argparse
import struct
import sys
import time
import uuid
from pathlib import Path


# --- MBR ------------------------------------------------------------------

MBR_BOOTCODE_END = 0x1BE
MBR_SIG_OFFSET = 0x1FE
SECTOR_SIZE = 512
PARTITION_START_LBA = 2048
PARTITION_START_OFFSET = PARTITION_START_LBA * SECTOR_SIZE  # 0x100000

PART_TYPE_FAT16_LBA = 0x0E


def build_mbr(jpeg: bytes, fat_sector_count: int) -> bytes:
    if len(jpeg) > MBR_BOOTCODE_END:
        raise ValueError(
            f"JPEG is {len(jpeg)} bytes; must be ≤ {MBR_BOOTCODE_END} to fit "
            f"in MBR boot-code region without overwriting the partition table"
        )
    mbr = bytearray(SECTOR_SIZE)
    mbr[:len(jpeg)] = jpeg
    # Partition table entry #1: FAT16-LBA at LBA 2048.
    entry = bytearray(16)
    entry[0] = 0x00                              # status (non-active is fine)
    entry[1:4] = bytes([0xFE, 0xFF, 0xFF])       # dummy CHS start (use LBA)
    entry[4] = PART_TYPE_FAT16_LBA
    entry[5:8] = bytes([0xFE, 0xFF, 0xFF])       # dummy CHS end
    struct.pack_into("<I", entry, 8, PARTITION_START_LBA)
    struct.pack_into("<I", entry, 12, fat_sector_count)
    mbr[MBR_BOOTCODE_END:MBR_BOOTCODE_END + 16] = entry
    # Entries 2, 3, 4 left zero (unused).
    mbr[MBR_SIG_OFFSET:MBR_SIG_OFFSET + 2] = b"\x55\xAA"
    return bytes(mbr)


# --- VHD footer (fixed disk) ----------------------------------------------

VHD_FOOTER_SIZE = 512
VHD_TIMESTAMP_EPOCH = 946684800  # 2000-01-01 00:00:00 UTC


def vhd_chs(total_sectors: int) -> tuple[int, int, int]:
    """Compute CHS for the VHD geometry field per the MS VHD spec."""
    if total_sectors > 65535 * 16 * 255:
        total_sectors = 65535 * 16 * 255
    if total_sectors >= 65535 * 16 * 63:
        spt, heads = 255, 16
        cth = total_sectors // spt
    else:
        spt, heads = 17, 4
        cth = total_sectors // spt
        if cth >= heads * 1024 or heads > 16:
            spt, heads = 31, 16
            cth = total_sectors // spt
        if cth >= heads * 1024:
            spt, heads = 63, 16
            cth = total_sectors // spt
    cylinders = cth // heads
    return cylinders, heads, spt


def build_vhd_footer(disk_size_bytes: int) -> bytes:
    """Build a 512-byte fixed VHD footer per Microsoft's VHD spec."""
    total_sectors = disk_size_bytes // SECTOR_SIZE
    cyl, heads, spt = vhd_chs(total_sectors)
    timestamp = int(time.time()) - VHD_TIMESTAMP_EPOCH

    # Big-endian throughout. Layout:
    # 0..8   cookie "conectix"
    # 8..12  features (0x00000002)
    # 12..16 fileFormatVersion (0x00010000)
    # 16..24 dataOffset (0xFFFFFFFFFFFFFFFF for fixed)
    # 24..28 timestamp
    # 28..32 creatorApplication (e.g. "pglt")
    # 32..36 creatorVersion (0x00010000)
    # 36..40 creatorHostOS ("Wi2k")
    # 40..48 originalSize
    # 48..56 currentSize
    # 56..58 cylinders
    # 58..59 heads
    # 59..60 sectorsPerTrack
    # 60..64 diskType (2 = fixed)
    # 64..68 checksum  (computed last)
    # 68..84 uniqueId (16 bytes)
    # 84..85 savedState (0)
    # 85..512 reserved zeros
    footer = bytearray(VHD_FOOTER_SIZE)
    struct.pack_into(">8sIIQ I 4sI 4s QQ HBB I", footer, 0,
                     b"conectix",
                     0x00000002,
                     0x00010000,
                     0xFFFFFFFFFFFFFFFF,
                     timestamp,
                     b"pglt", 0x00010000, b"Wi2k",
                     disk_size_bytes, disk_size_bytes,
                     cyl, heads, spt,
                     2)
    # Checksum field at offset 64..68 is currently zero (correct for compute).
    footer[68:84] = uuid.uuid4().bytes
    footer[84] = 0
    # Checksum: one's complement of the sum of all bytes (checksum bytes as 0).
    chksum = sum(footer) & 0xFFFFFFFF
    chksum ^= 0xFFFFFFFF
    struct.pack_into(">I", footer, 64, chksum)
    return bytes(footer)


# --- Composer -------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jpg", required=True, type=Path,
                    help="cover JPEG (must be ≤ 446 bytes)")
    ap.add_argument("--fat", required=True, type=Path,
                    help="FAT16 partition image (output of build_fat.py)")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    jpg = args.jpg.read_bytes()
    if not jpg.startswith(b"\xFF\xD8\xFF"):
        print(f"[error] {args.jpg} doesn't start with JPEG SOI", file=sys.stderr)
        return 2
    print(f"[jpg]   {args.jpg} : {len(jpg)} bytes "
          f"({MBR_BOOTCODE_END - len(jpg)} bytes free in MBR boot region)")

    fat = args.fat.read_bytes()
    if len(fat) % SECTOR_SIZE != 0:
        print(f"[error] FAT image size {len(fat)} not sector-aligned",
              file=sys.stderr)
        return 2
    fat_sector_count = len(fat) // SECTOR_SIZE
    # Confirm the FAT boot sector starts with a FAT-style jump (EB xx 90 or E9).
    if fat[0] not in (0xEB, 0xE9):
        print(f"[warn] FAT image first byte {fat[0]:#x} unexpected — "
              f"may not mount", file=sys.stderr)
    print(f"[fat]   {args.fat} : {len(fat)} bytes ({fat_sector_count} sectors)")

    mbr = build_mbr(jpg, fat_sector_count)
    assert len(mbr) == SECTOR_SIZE
    print(f"[mbr]   built 512-byte MBR (JPEG in boot code, FAT16-LBA "
          f"partition LBA {PARTITION_START_LBA}..{PARTITION_START_LBA + fat_sector_count - 1})")

    # Disk content = MBR + zeros until LBA 2048 + FAT partition.
    pre_pad = PARTITION_START_OFFSET - SECTOR_SIZE
    disk_size = SECTOR_SIZE + pre_pad + len(fat)
    print(f"[disk]  total disk size = {disk_size} bytes "
          f"({disk_size // (1024*1024)} MiB)")

    footer = build_vhd_footer(disk_size)
    print(f"[vhd]   built 512-byte footer "
          f"(cookie={footer[:8]!r}, "
          f"disk_type={footer[60]:#x}, "
          f"checksum={struct.unpack('>I', footer[64:68])[0]:#010x})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("wb") as f:
        f.write(mbr)
        f.write(b"\x00" * pre_pad)
        f.write(fat)
        f.write(footer)
    final_size = args.out.stat().st_size
    print(f"[out]   wrote {args.out} : {final_size} bytes "
          f"(disk={disk_size}, footer={VHD_FOOTER_SIZE})")

    # --- self-checks ---
    with args.out.open("rb") as f:
        data = f.read()
    assert data[:3] == b"\xFF\xD8\xFF", "JPEG SOI missing at offset 0"
    print(f"[check] JPEG SOI present at offset 0")
    assert data[MBR_SIG_OFFSET:MBR_SIG_OFFSET + 2] == b"\x55\xAA", \
        "MBR signature missing"
    print(f"[check] MBR 55 AA signature present at offset {MBR_SIG_OFFSET:#x}")
    # Parse the partition table entry.
    pte = data[MBR_BOOTCODE_END:MBR_BOOTCODE_END + 16]
    ptype = pte[4]
    plba = struct.unpack_from("<I", pte, 8)[0]
    psize = struct.unpack_from("<I", pte, 12)[0]
    assert ptype == PART_TYPE_FAT16_LBA, f"partition type {ptype:#x} != FAT16-LBA"
    assert plba == PARTITION_START_LBA, f"partition start LBA {plba} != {PARTITION_START_LBA}"
    print(f"[check] partition table: type={ptype:#x} (FAT16-LBA), "
          f"LBA {plba}, {psize} sectors")
    # FAT boot sector at the partition offset.
    fat_bs = data[PARTITION_START_OFFSET:PARTITION_START_OFFSET + 4]
    assert fat_bs[0] in (0xEB, 0xE9), \
        f"FAT BS not at expected offset; first byte {fat_bs[0]:#x}"
    print(f"[check] FAT boot sector found at offset {PARTITION_START_OFFSET:#x} "
          f"(first byte {fat_bs[0]:#x})")
    # VHD footer cookie.
    assert data[-VHD_FOOTER_SIZE:-VHD_FOOTER_SIZE + 8] == b"conectix", \
        "VHD footer cookie missing at EOF-512"
    print(f"[check] VHD footer cookie 'conectix' at EOF-{VHD_FOOTER_SIZE}")
    # Re-verify footer checksum.
    f_bytes = bytearray(data[-VHD_FOOTER_SIZE:])
    embedded_cksum = struct.unpack(">I", f_bytes[64:68])[0]
    f_bytes[64:68] = b"\x00\x00\x00\x00"
    recomputed = (sum(f_bytes) & 0xFFFFFFFF) ^ 0xFFFFFFFF
    assert recomputed == embedded_cksum, \
        f"footer checksum mismatch: stored {embedded_cksum:#x} vs {recomputed:#x}"
    print(f"[check] VHD footer checksum self-consistent: {embedded_cksum:#010x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
