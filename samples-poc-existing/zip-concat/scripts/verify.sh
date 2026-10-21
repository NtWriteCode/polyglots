#!/usr/bin/env bash
# Shows which of the two archives each local ZIP reader picks.
f="$1"
[ -f "$f" ] || { echo "usage: $0 <file>"; exit 1; }

echo "== file(1)"
file -b "$f"

echo; echo "== 7-Zip (7z l)"
7z l "$f" 2>&1 | grep -E "SHIPPING|WARNING|There are data|Headers Error|Type =|Offset ="

echo; echo "== Info-ZIP (unzip -l)"
unzip -l "$f" 2>&1 | grep -E "SHIPPING|warning|extra bytes"

echo; echo "== Python zipfile"
python3 -c 'import sys, zipfile; print(zipfile.ZipFile(sys.argv[1]).namelist())' "$f"

echo; echo "== ZIP structures in the file"
python3 - "$f" <<'PY'
import sys
data = open(sys.argv[1], "rb").read()
for name, sig in (("local file header", b"PK\x03\x04"), ("end of central dir", b"PK\x05\x06")):
    hits, i = [], data.find(sig)
    while i != -1:
        hits.append(i)
        i = data.find(sig, i + 1)
    print(f"{name:20} at offsets {hits}")
PY
