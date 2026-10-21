#!/usr/bin/env python3
"""Turns a compiled PE into a PE + HTA polyglot.

The HTA goes into the overlay (after the last section), where the Windows
loader never looks. mshta reads the file as HTML, so the binary in between
is wrapped in an HTML comment: `<!--` replaces the unused DOS header fields
at offset 2..5 (e_cblp, e_cp), `-->` opens the overlay. The build fails if
the binary itself would close the comment early.
"""
import argparse
import struct

# Goes in front of the HTA file: closes the HTML comment opened in the DOS header.
COMMENT_END = b"-->\r\n"


def pe_end_of_last_section(pe):
    """File offset where the last section's raw data ends: the start of the overlay."""
    assert pe[:2] == b"MZ", "missing MZ magic"
    e_lfanew = struct.unpack_from("<I", pe, 0x3C)[0]
    assert pe[e_lfanew:e_lfanew + 4] == b"PE\0\0", "missing PE signature"
    n_sections = struct.unpack_from("<H", pe, e_lfanew + 6)[0]
    size_opt_hdr = struct.unpack_from("<H", pe, e_lfanew + 20)[0]
    table = e_lfanew + 24 + size_opt_hdr
    end = 0
    for i in range(n_sections):
        raw_size, raw_ptr = struct.unpack_from("<II", pe, table + 40 * i + 16)
        if raw_ptr:  # 0 = no file presence (.bss)
            end = max(end, raw_ptr + raw_size)
    assert 0 < end <= len(pe), "bad section layout"
    return end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pe")
    ap.add_argument("hta")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    HTA = COMMENT_END + open(a.hta, "rb").read()

    pe = bytearray(open(a.pe, "rb").read())
    end = pe_end_of_last_section(pe)
    del pe[end:]  # drop any existing overlay

    body = bytes(pe[6:])
    for seq in (b"-->", b"--!>"):
        assert seq not in body, f"PE body contains {seq!r}: the HTML comment would end early"
    assert not body.startswith((b">", b"->")), "comment would close right after <!--"
    pe[2:6] = b"<!--"

    with open(a.out, "wb") as f:
        f.write(pe + HTA)
    print(f"wrote {a.out}: PE ends at {end:#x}, HTA overlay {len(HTA)} bytes")


if __name__ == "__main__":
    main()
