#!/usr/bin/env python3
"""Appends the HTML page to the DLL's overlay and hides the PE from the HTML parser.

Offsets 2..5 of the DOS header (e_cblp, e_cp) are ignored by the Windows loader,
so `<!--` goes there. A browser then sees `MZ<!-- ...binary... --><!DOCTYPE html>...`
and renders "MZ" plus the page. That only works if the binary never closes the
comment early, which the build checks.
"""
import argparse
from pathlib import Path

from pe import section_end


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dll")
    ap.add_argument("page")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pe = bytearray(Path(a.dll).read_bytes())
    end = section_end(pe)
    del pe[end:]  # drop any linker padding so the page starts right after the last section
    pe[2:6] = b"<!--"

    # The opener's own dashes count too (`<!-->` closes at once), so scan with them prepended.
    body = b"--" + bytes(pe[6:])
    for closer in (b"-->", b"--!>"):
        if closer in body:
            raise SystemExit(f"PE bytes contain {closer!r} at {body.index(closer) + 4:#x}: would end the HTML comment early")

    Path(a.out).write_bytes(bytes(pe) + b"-->" + Path(a.page).read_bytes())
    print(f"wrote {a.out}: PE {end} bytes, page appended at {end:#x}")


if __name__ == "__main__":
    main()
