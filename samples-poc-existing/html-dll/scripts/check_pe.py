#!/usr/bin/env python3
"""Checks that the polyglot is still a DLL exporting Run and that its overlay is exactly the page."""
import sys
from pathlib import Path

from pe import export_names, is_dll, section_end

data = Path(sys.argv[1]).read_bytes()
page = b"-->" + Path(sys.argv[2]).read_bytes()
end = section_end(data)
exports = export_names(data)
print(f"DLL={is_dll(data)} exports={exports} overlay at {end:#x}, {len(data) - end} bytes")

assert is_dll(data), "IMAGE_FILE_DLL not set"
assert "Run" in exports, "no Run export"
assert data[2:6] == b"<!--", "DOS header does not open an HTML comment"
assert data[end:] == page, "overlay is not the page"
for closer in (b"-->", b"--!>"):
    assert closer not in b"--" + data[6:end], f"PE bytes contain {closer!r}: comment closes early"
print("PE and overlay OK")
