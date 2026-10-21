#!/usr/bin/env python3
"""
build_lnk.py — write a Windows shortcut (LNK) that opens calc.exe.

Hand-written per MS-SHLLINK, standard library only. No LinkTargetIDList: tools
that build one off-Windows guess every path part's type (pylnk3 marked
calc.exe as a folder), and Windows then shows an empty target. Instead the
target is given twice, both of which Windows resolves on its own:
  - LinkInfo:  local path on a fixed drive (C:\\Windows\\System32\\calc.exe)
  - EnvironmentVariableDataBlock: %windir%\\System32\\calc.exe
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

LINK_CLSID = bytes.fromhex("0114020000000000c000000000000046")

HAS_LINK_INFO = 0x002
HAS_NAME = 0x004
HAS_WORKING_DIR = 0x010
IS_UNICODE = 0x080
HAS_EXP_STRING = 0x200

FILE_ATTRIBUTE_ARCHIVE = 0x20
SW_SHOWNORMAL = 1
DRIVE_FIXED = 3


def string_data(s: str) -> bytes:
    # CountCharacters + UTF-16LE, no terminator.
    return struct.pack("<H", len(s)) + s.encode("utf-16-le")


def link_info(local_path: str) -> bytes:
    volume_id = struct.pack("<IIII", 0x11, DRIVE_FIXED, 0, 0x10) + b"\0"  # empty label
    base = local_path.encode("ascii") + b"\0"
    suffix = b"\0"
    header_size = 0x1C
    volume_off = header_size
    base_off = volume_off + len(volume_id)
    suffix_off = base_off + len(base)
    size = suffix_off + len(suffix)
    header = struct.pack("<IIIIIII", size, header_size, 1,  # VolumeIDAndLocalBasePath
                         volume_off, base_off, 0, suffix_off)
    return header + volume_id + base + suffix


def env_block(target: str) -> bytes:
    ansi = target.encode("ascii").ljust(260, b"\0")
    wide = target.encode("utf-16-le").ljust(520, b"\0")
    return struct.pack("<II", 0x314, 0xA0000001) + ansi + wide


def build(target: str, env_target: str, workdir: str, description: str) -> bytes:
    flags = HAS_LINK_INFO | HAS_NAME | HAS_WORKING_DIR | IS_UNICODE | HAS_EXP_STRING
    header = struct.pack("<I16sII8s8s8sIiIHHII",
                         0x4C, LINK_CLSID, flags, FILE_ATTRIBUTE_ARCHIVE,
                         b"\0" * 8, b"\0" * 8, b"\0" * 8,  # times unknown
                         0, 0, SW_SHOWNORMAL, 0, 0, 0, 0)
    return (header
            + link_info(target)
            + string_data(description)
            + string_data(workdir)
            + env_block(env_target)
            + b"\0\0\0\0")  # TerminalBlock


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=r"C:\Windows\System32\calc.exe")
    ap.add_argument("--env-target", default=r"%windir%\System32\calc.exe")
    ap.add_argument("--workdir", default=r"C:\Windows\System32")
    ap.add_argument("--description", default="Polyglot demo V4 — opens Calculator")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    data = build(args.target, args.env_target, args.workdir, args.description)
    args.out.write_bytes(data)
    print(f"[lnk]   wrote {args.out} : {len(data)} bytes targeting {args.target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
