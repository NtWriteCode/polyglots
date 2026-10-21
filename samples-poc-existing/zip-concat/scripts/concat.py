#!/usr/bin/env python3
"""Glues two ZIPs and rewrites the second one's offsets to count from the start of the file.

Plain `cat` leaves the second ZIP's offsets relative to its own start. Lenient
readers (unzip, Python) fix that up; Windows Explorer refuses the file instead.
With absolute offsets the second ZIP is a normal archive with a prefix, like a
self-extractor, so Explorer opens it too. No ZIP64 support; the parts are tiny.
"""
import argparse
import struct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("first")
    ap.add_argument("second")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    first = open(a.first, "rb").read()
    second = bytearray(open(a.second, "rb").read())
    shift = len(first)

    eocd = second.rfind(b"PK\x05\x06")
    count = struct.unpack_from("<H", second, eocd + 10)[0]
    cd = struct.unpack_from("<I", second, eocd + 16)[0]

    pos = cd
    for _ in range(count):
        assert second[pos:pos + 4] == b"PK\x01\x02", "central directory entry expected"
        lfh = struct.unpack_from("<I", second, pos + 42)[0]
        struct.pack_into("<I", second, pos + 42, lfh + shift)
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", second, pos + 28)
        pos += 46 + name_len + extra_len + comment_len
    struct.pack_into("<I", second, eocd + 16, cd + shift)

    with open(a.out, "wb") as f:
        f.write(first + second)


if __name__ == "__main__":
    main()
