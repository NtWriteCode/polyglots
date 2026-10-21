#!/usr/bin/env python3
"""Walks the GIF blocks with stdlib only, then compares pixels with Pillow.

Passes when there is exactly one Comment Extension, it holds the PHP string,
no other "<?" exists in the file, and the pixels equal the comment-free GIF.
"""
import sys

from PIL import Image

from build import read_php


def color_table(flags):
    return 3 << ((flags & 7) + 1) if flags & 0x80 else 0


def sub_blocks(data, i):
    """Joins data sub-blocks; returns (payload, offset after the 0x00 terminator)."""
    out = bytearray()
    while data[i]:
        out += data[i + 1:i + 1 + data[i]]
        i += 1 + data[i]
    return bytes(out), i + 1


def walk(data):
    """Yields (offset, kind, payload) for every block after the Global Color Table."""
    i = 13 + color_table(data[10])
    while True:
        b = data[i]
        if b == 0x3B:  # Trailer
            yield i, "trailer", b""
            return
        if b == 0x2C:  # Image Descriptor, local color table, LZW min code size, sub-blocks
            j = i + 10 + color_table(data[i + 9]) + 1
            _, j = sub_blocks(data, j)
            yield i, "image", b""
        elif b == 0x21:  # Extension: label byte, then sub-blocks
            payload, j = sub_blocks(data, i + 2)
            yield i, f"extension 0x{data[i + 1]:02X}", payload
        else:
            raise SystemExit(f"unknown block 0x{b:02X} at offset {i}")
        i = j


def main():
    poly, clean, php = sys.argv[1], sys.argv[2], read_php(sys.argv[3])
    data = open(poly, "rb").read()
    print(f"{'offset':>6}  block")
    comments = []
    for off, kind, payload in walk(data):
        print(f"{off:6}  {kind}" + (f"  {payload!r}" if payload else ""))
        if kind == "extension 0xFE":
            comments.append(payload)

    ok = True
    if comments != [php]:
        print(f"FAIL: expected one Comment Extension with the PHP string, got {comments!r}")
        ok = False
    if data.count(b"<?") != 1:
        print(f"FAIL: '<?' occurs {data.count(b'<?')} times, expected 1")
        ok = False
    a, b = Image.open(poly), Image.open(clean)
    same = a.convert("RGB").tobytes() == b.convert("RGB").tobytes()
    if not same:
        print("FAIL: pixels differ from the comment-free GIF")
        ok = False
    print(f"PIL: {a.format} {a.size}, pixels identical to {clean}: {same}")
    print(f"PIL comment: {a.info.get('comment')!r}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
