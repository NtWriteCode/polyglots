#!/usr/bin/env python3
"""Draws the demo GIF (input/image.gif): white 320x120 GIF89a, one line of black text."""
import argparse

from PIL import Image, ImageDraw, ImageFont

SIZE = (320, 120)
TEXT = "This is the GIF side of the polyglot"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = ap.parse_args().out

    img = Image.new("P", SIZE, 0)
    img.putpalette([255, 255, 255, 0, 0, 0])  # 0 = white, 1 = black
    font = ImageFont.load_default(size=18)
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = d.textbbox((0, 0), TEXT, font=font)
    d.text(((SIZE[0] - x1 - x0) // 2, (SIZE[1] - y1 - y0) // 2), TEXT, fill=1, font=font)
    img.info["version"] = b"89a"  # the Comment Extension is a GIF89a feature
    img.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
