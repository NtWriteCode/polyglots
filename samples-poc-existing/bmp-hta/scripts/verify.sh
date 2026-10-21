#!/usr/bin/env bash
# Checks both sides of the polyglot. Exits non-zero on any failure; missing tools are skipped.
f="$1"; clean="$2"; hta_file="$3"
[ -f "$f" ] && [ -f "$clean" ] && [ -f "$hta_file" ] || { echo "usage: $0 <polyglot.bmp> <clean.bmp> <script.hta>"; exit 1; }
rc=0
fail() { echo "FAIL: $*"; rc=1; }

echo "== file(1)"
file -b "$f"

echo; echo "== PIL: opens, pixels equal the clean BMP"
python3 - "$f" "$clean" <<'PY' || fail "PIL check"
import sys
from PIL import Image, ImageChops
poly, clean = (Image.open(p).convert("RGB") for p in sys.argv[1:])
print(f"{poly.size} {poly.mode}, identical pixels: {ImageChops.difference(poly, clean).getbbox() is None}")
sys.exit(0 if ImageChops.difference(poly, clean).getbbox() is None else 1)
PY

echo; echo "== ImageMagick identify"
if command -v identify >/dev/null; then
    identify "$f" || fail "identify"
else
    echo "skipped: identify not installed"
fi

echo; echo "== HTA side: header comment, trailing script block"
python3 - "$f" "$clean" "$(dirname "$0")" "$hta_file" <<'PY' || fail "HTA side"
import struct, sys
sys.path.insert(0, sys.argv[3])
from polyglot import COMMENT_END
hta = COMMENT_END + open(sys.argv[4], "rb").read()  # the appended block

data = open(sys.argv[1], "rb").read()
clean_len = len(open(sys.argv[2], "rb").read())
ok = True
def check(cond, msg):
    global ok
    print(("ok   " if cond else "FAIL ") + msg)
    ok &= cond
check(data[:2] == b"BM", "magic BM")
check(data[6:10] == b"<!--", "bfReserved1/2 = '<!--'")
check(struct.unpack_from("<I", data, 2)[0] == len(data), "bfSize = full file size")
check(data[clean_len:] == hta, "trailing block is exactly the expected script")
check(b"-->" not in data[10:clean_len] and b"--!>" not in data[10:clean_len], "no comment terminator inside the BMP body")
print("HTA side as a parser sees it:", data[:2] + b"??" + data[6:10] + b" ...pixels... " + data[clean_len:clean_len+11] + b"...")
sys.exit(0 if ok else 1)
PY

echo; echo "== REMnux container (exiftool, identify)"
if command -v docker >/dev/null && docker image inspect am-lab-remnux:latest >/dev/null 2>&1; then
    docker run --rm -v "$PWD:/work:ro" -w /work --entrypoint sh am-lab-remnux:latest \
        -c "exiftool $f; identify $f" || fail "REMnux container"
else
    echo "skipped: docker or am-lab-remnux:latest image not available"
fi

echo
[ $rc -eq 0 ] && echo "VERIFY OK" || echo "VERIFY FAILED"
exit $rc
