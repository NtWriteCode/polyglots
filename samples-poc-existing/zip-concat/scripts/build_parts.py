#!/usr/bin/env python3
"""Builds the two halves: a decoy ZIP with a real PDF, and a harmless "payload" ZIP."""
import argparse
import zipfile
from pathlib import Path


def tiny_pdf(text):
    # Minimal one-page PDF with correct xref offsets.
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


# Stands in for the AutoIt trojan. It only prints a message.
PAYLOAD_BAT = (
    "@echo off\r\n"
    "echo This came from the SECOND (hidden) ZIP.\r\n"
    "echo A tool that only reads the first ZIP never saw this file.\r\n"
    "pause\r\n"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out = Path(ap.parse_args().out)

    with zipfile.ZipFile(out / "decoy.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("SHIPPING_INV_PL_BL.pdf", tiny_pdf("Shipping invoice - nothing to see here"))

    with zipfile.ZipFile(out / "payload.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("SHIPPING_INV_PL_BL.pdf.bat", PAYLOAD_BAT)

    print(f"wrote {out / 'decoy.zip'} and {out / 'payload.zip'}")


if __name__ == "__main__":
    main()
