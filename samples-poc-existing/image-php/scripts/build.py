#!/usr/bin/env python3
"""Hides PHP in a GIF Comment Extension, right after the GIF header.

PHP prints everything outside `<?php ... ?>` as-is, so running the file through
php dumps the GIF bytes and then the message. Image tools ignore comments.
"""
import argparse
from pathlib import Path


def read_php(path):
    """The PHP snippet without the trailing newline, as bytes for the comment block."""
    return Path(path).read_bytes().rstrip(b"\r\n")


def comment_block(data):
    # 0x21 0xFE, data sub-blocks of at most 255 bytes, 0x00 terminator.
    out = bytearray(b"\x21\xfe")
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        out += bytes([len(chunk)]) + chunk
    return bytes(out + b"\x00")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", required=True, help="the clean GIF")
    ap.add_argument("--php", required=True, help="the PHP snippet")
    ap.add_argument("--out", required=True, help="the polyglot GIF")
    a = ap.parse_args()
    gif, php = bytearray(Path(a.gif).read_bytes()), read_php(a.php)

    if gif[:6] == b"GIF87a":
        gif[:6] = b"GIF89a"  # the Comment Extension is a GIF89a feature
    if gif[:6] != b"GIF89a":
        raise SystemExit(f"{a.gif} is not a GIF")

    # Header (6) + Logical Screen Descriptor (7) + Global Color Table.
    flags = gif[10]
    end = 13 + (3 << ((flags & 7) + 1) if flags & 0x80 else 0)
    if gif[end] not in (0x2C, 0x21):
        raise SystemExit("expected an Image Descriptor or an Extension after the Global Color Table")

    poly = bytes(gif[:end]) + comment_block(php) + bytes(gif[end:])
    # Compressed pixels could contain "<?" by chance; PHP would start parsing there too.
    if poly.count(b"<?") != 1:
        raise SystemExit("found '<?' more than once: in the image bytes or in the PHP; PHP would run from there")

    Path(a.out).write_bytes(poly)
    print(f"wrote {a.out} ({len(poly)} bytes, comment at offset {end})")


if __name__ == "__main__":
    main()
