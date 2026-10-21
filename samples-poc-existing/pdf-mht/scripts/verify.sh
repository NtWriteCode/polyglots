#!/usr/bin/env bash
# Shows each side through its own readers: PDF tools on the host, pdfid/qpdf/olevba in the
# REMnux image (skipped without docker). Exits non-zero if either side's message is missing.
f="$1"
[ -f "$f" ] || { echo "usage: $0 <file>"; exit 1; }
fail=0

echo "== file(1)"
file -b "$f"

echo; echo "== PDF side: pdfinfo, pdftotext (host)"
pdfinfo "$f" | grep -E "^(Pages|Page size|File size)"
pdftotext "$f" - | grep -F "This is the PDF side of the polyglot" || { echo "FAIL: PDF text missing"; fail=1; }

echo; echo "== MHT side: MIME parts and the ActiveMime container (python stdlib)"
python3 - "$f" <<'PY' || fail=1
import email, sys, zlib
data = open(sys.argv[1], "rb").read()
start = data.find(b"MIME-Version")
print(f"MIME-Version header at offset {start} (PDF prefix is {start} bytes)")
parts = [p for p in email.message_from_bytes(data[start:]).walk() if not p.is_multipart()]
for p in parts:
    print(f"{p.get_content_type():20} {len(p.get_payload(decode=True))} bytes  {p['Content-Location']}")
mso = next(p for p in parts if p.get_content_type() == "application/x-mso").get_payload(decode=True)
assert mso.startswith(b"ActiveMime"), "editdata.mso lacks the ActiveMime magic"
ole = zlib.decompress(mso[0x32:])
assert ole.startswith(b"\xd0\xcf\x11\xe0"), "ActiveMime payload is not an OLE2 file"
print(f"editdata.mso: ActiveMime header, zlib at 0x32, OLE2 file of {len(ole)} bytes")
PY

if ! command -v docker >/dev/null || ! docker image inspect am-lab-remnux:latest >/dev/null 2>&1; then
    echo; echo "== skipped: docker / am-lab-remnux:latest not available (qpdf, pdfid, olevba)"
    exit $fail
fi
remnux() { docker run --rm -v "$PWD:/work:ro" -w /work --entrypoint sh am-lab-remnux:latest -c "$1"; }

echo; echo "== PDF side: qpdf --check, pdfid.py -e (REMnux)"
remnux "qpdf --check '$f'; pdfid.py -e '$f' | grep -E 'obj|stream|%%EOF'"

echo; echo "== MHT side: olevba on the whole file (REMnux)"
# olevba's MIME pre-parse starts at the PDF's "/Contents" and Python 3's email parser then
# rejects the PDF lines as headers, so the file is misread as plain text. Shown, not required.
remnux "olevba '$f' 2>/dev/null" | grep -E "^Type:|^VBA MACRO|AutoOpen|MsgBox" | head -4

echo; echo "== MHT side: olevba on the carved MHT (REMnux)"
out=$(remnux "python3 -c 'd=open(\"$f\",\"rb\").read(); open(\"/tmp/carved.mht\",\"wb\").write(d[d.find(b\"MIME-Version\"):])' && olevba /tmp/carved.mht 2>/dev/null")
echo "$out" | grep -vE "^(olevba|=+$|WARNING)"
echo "$out" | grep -q "^Sub AutoOpen" && echo "$out" | grep -q 'MsgBox "This came from the MHT side' \
    || { echo "FAIL: olevba did not show the macro"; fail=1; }

exit $fail
