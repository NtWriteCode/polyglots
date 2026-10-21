#!/usr/bin/env python3
"""Draws the clean BMP: white 320x120, 24-bit, one line of black text. PIL is only used here."""
import argparse

from PIL import Image, ImageDraw, ImageFont

TEXT = "This is the BMP side of the polyglot"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = ap.parse_args().out

    img = Image.new("RGB", (320, 120), "white")
    try:
        font = ImageFont.load_default(size=16)  # Pillow >= 10.1
    except TypeError:
        font = ImageFont.load_default()
    ImageDraw.Draw(img).text((10, 50), TEXT, fill="black", font=font)
    img.save(out, "BMP")  # 24-bit BI_RGB, pixel data at offset 54
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
