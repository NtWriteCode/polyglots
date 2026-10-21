#!/usr/bin/env python3
"""
build_fat.py — produce a FAT16 image containing payload.lnk at root.

1. Allocate a zero-filled raw image at the requested size.
2. Run `mkfs.fat -F 16` to write a valid FAT16 boot sector and tables.
3. Open the image with pyfatfs and copy in payload.lnk.

Output: a raw FAT16 partition image (not a disk image — there is no MBR
here). The V4 polyglot composer places this at LBA 2048 of the VHD's
disk region.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from pyfatfs.PyFatFS import PyFatFS  # type: ignore


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size-mb", type=int, default=16,
                    help="FAT partition size in MiB (must be ≥ ~12 for FAT16)")
    ap.add_argument("--label", default="POLYGLOT")
    ap.add_argument("--payload", required=True, type=Path,
                    help="file to copy into the FAT root (e.g. payload.lnk)")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    size_bytes = args.size_mb * 1024 * 1024
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("wb") as f:
        f.truncate(size_bytes)

    subprocess.run(
        ["/usr/sbin/mkfs.fat", "-F", "16", "-n", args.label, str(args.out)],
        check=True, capture_output=True,
    )
    print(f"[fat]   mkfs.fat -F 16 -n {args.label} on {size_bytes}-byte image OK")

    payload_bytes = args.payload.read_bytes()
    fs = PyFatFS(str(args.out))
    fs.writebytes(f"/{args.payload.name}", payload_bytes)
    fs.close()
    print(f"[fat]   wrote /{args.payload.name} ({len(payload_bytes)} bytes) "
          f"into FAT root")
    return 0


if __name__ == "__main__":
    sys.exit(main())
