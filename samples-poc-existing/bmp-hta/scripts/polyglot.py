#!/usr/bin/env python3
"""Turns a BMP and an HTA script into a BMP/HTA polyglot. Header patched with struct, script appended after the pixels.

Byte layout of the result:
  0..1    "BM"                       magic, also the only visible text on the HTA side
  2..5    bfSize                     set to the FULL file size (ImageMagick 7 refuses the file otherwise)
  6..9    "<!--"                     bfReserved1/2, ignored by image readers, opens an HTML comment
  10..    rest of the BMP            hidden inside the comment; must not contain "-->" or "--!>"
  end     "-->" + the HTA file       closes the comment, then the HTA payload
BMP readers stop at the end of the pixel data, so the trailing block is invisible to them.
"""
import argparse
import struct

# Goes in front of the HTA file: closes the HTML comment opened in the BMP header.
COMMENT_END = b"-->"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bmp")
    ap.add_argument("hta")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    HTA = COMMENT_END + open(a.hta, "rb").read()

    bmp = bytearray(open(a.bmp, "rb").read())
    assert bmp[:2] == b"BM", "not a BMP"
    assert struct.unpack_from("<I", bmp, 2)[0] == len(bmp), "bfSize must match the clean file"

    # The HTML comment opened at offset 6 must stay open until our own "-->".
    for end in (b"-->", b"--!>"):
        assert end not in bmp[10:], f"{end!r} inside the BMP body would end the comment early"

    bmp[6:10] = b"<!--"
    struct.pack_into("<I", bmp, 2, len(bmp) + len(HTA))

    with open(a.out, "wb") as f:
        f.write(bmp + HTA)
    print(f"wrote {a.out} ({len(bmp)} BMP bytes + {len(HTA)} HTA bytes)")


if __name__ == "__main__":
    main()
