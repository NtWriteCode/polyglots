"""
zip_offset.py — patch all internal ZIP offsets so the archive remains
structurally coherent after being concatenated onto a non-ZIP prefix.

Lenient parsers (7-Zip, Info-ZIP, Python `zipfile`) self-correct missing
offsets, but stricter parsers — notably LibreOffice's OOXML loader and
some Java ZipFile modes — refuse files where the recorded offsets don't
point to the actual local file headers. This module performs the
adjustment.

Only handles non-ZIP64 archives (4 GiB total / 65535 entries cap), which
covers every practical OOXML/JAR/APK we care about.
"""
from __future__ import annotations

import struct

EOCD_SIG = b"PK\x05\x06"
CD_SIG = b"PK\x01\x02"
LFH_SIG = b"PK\x03\x04"

EOCD_FMT = "<IHHHHIIH"  # sig, disk, cd_disk, n_disk, n_total, cd_size, cd_off, comment_len
CD_FIXED_LEN = 46
EOCD_FIXED_LEN = 22


def find_eocd(data: bytes) -> int:
    """Locate the EOCD signature, scanning backward from EOF (max 65557 B)."""
    max_back = min(len(data), 65557)
    start = len(data) - max_back
    off = data.rfind(EOCD_SIG, start)
    if off < 0:
        raise ValueError("EOCD signature PK\\x05\\x06 not found")
    return off


def shift_offsets(zip_bytes: bytes, delta: int) -> bytes:
    """Return zip_bytes with every internal offset increased by `delta`.

    After this, prepending `delta` bytes of arbitrary data yields a file
    that strict ZIP parsers accept as a normal (not SFX) archive.
    """
    if delta < 0:
        raise ValueError("delta must be >= 0")
    if delta == 0:
        return zip_bytes

    data = bytearray(zip_bytes)
    eocd_off = find_eocd(data)
    sig, _disk, _cd_disk, _n_disk, n_total, cd_size, cd_off, comment_len = \
        struct.unpack_from(EOCD_FMT, data, eocd_off)
    if sig != 0x06054B50:
        raise ValueError("EOCD signature mismatch after parse")

    # Patch EOCD: cd_offset += delta
    struct.pack_into("<I", data, eocd_off + 16, cd_off + delta)

    # Walk CD entries and patch each local_header_offset += delta.
    off = cd_off
    end = cd_off + cd_size
    for i in range(n_total):
        if off + CD_FIXED_LEN > end:
            raise ValueError(f"CD entry #{i} runs past CD region")
        if data[off:off + 4] != CD_SIG:
            raise ValueError(f"CD entry #{i} missing PK\\x01\\x02 at {off:#x}")
        name_len = struct.unpack_from("<H", data, off + 28)[0]
        extra_len = struct.unpack_from("<H", data, off + 30)[0]
        cmt_len = struct.unpack_from("<H", data, off + 32)[0]
        local_off = struct.unpack_from("<I", data, off + 42)[0]
        struct.pack_into("<I", data, off + 42, local_off + delta)
        off += CD_FIXED_LEN + name_len + extra_len + cmt_len

    if off != end:
        raise ValueError(f"CD walk ended at {off:#x}, expected {end:#x}")

    return bytes(data)
