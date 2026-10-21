#!/usr/bin/env bash
# Checks both sides of the polyglot. Exits non-zero on failure, skips missing tools.
set -uo pipefail
f="$1"; hta_file="$2"
[ -f "$f" ] && [ -f "$hta_file" ] || { echo "usage: $0 <polyglot.exe> <script.hta>"; exit 1; }
here=$(dirname "$0")
pe_msg="This came from the PE side of the polyglot"
rc=0

echo "== file(1)"
file -b "$f"

echo; echo "== PE headers, overlay and HTML view"
overlay=$(python3 - "$f" "$here" "$hta_file" <<'PY'
import sys, html.parser
sys.path.insert(0, sys.argv[2])
from build_polyglot import COMMENT_END, pe_end_of_last_section
HTA = COMMENT_END + open(sys.argv[3], "rb").read()

data = open(sys.argv[1], "rb").read()
end = pe_end_of_last_section(data)
assert data[2:6] == b"<!--", "DOS header bytes 2..5 are not <!--"
assert data[end:] == HTA, "overlay is not the expected HTA block"
body = data[6:end]
assert b"-->" not in body and b"--!>" not in body, "comment ends early inside the PE"

class View(html.parser.HTMLParser):
    comments, scripts = 0, []
    def handle_comment(self, _): self.comments += 1
    def handle_starttag(self, tag, attrs):
        if tag == "script": self.scripts.append(dict(attrs).get("language"))
p = View(); p.feed(data.decode("latin-1")); p.close()
assert p.comments == 1 and p.scripts == ["VBScript"], f"HTML view: {p.comments} comments, scripts {p.scripts}"

print(f"PE ok, overlay starts at {end:#x} ({len(data) - end} bytes); HTML view: 1 comment + 1 VBScript block", file=sys.stderr)
print(end)
PY
) || rc=1

echo; echo "== PE side: wine"
if command -v wine >/dev/null; then
    out=$(env -u DISPLAY WINEDEBUG=-all timeout 30 wine "$f" 2>/dev/null | tr -d "\r")
    echo "$out"
    [ "$out" = "$pe_msg" ] || { echo "FAIL: wine did not print the PE message"; rc=1; }
else
    echo "skipped: wine not installed"
fi

echo; echo "== Overlay offset per pefile (REMnux container)"
if command -v docker >/dev/null && docker image inspect am-lab-remnux:latest >/dev/null 2>&1; then
    got=$(docker run --rm --pull=never -v "$PWD:/work:ro" -w /work --entrypoint python3 am-lab-remnux:latest \
        -c "import pefile, sys; print(pefile.PE(sys.argv[1]).get_overlay_data_start_offset())" "$f")
    echo "pefile says $got, expected $overlay"
    [ "$got" = "$overlay" ] || { echo "FAIL: overlay offsets disagree"; rc=1; }
else
    echo "skipped: docker or am-lab-remnux image not available"
fi

echo; [ $rc -eq 0 ] && echo "verify: OK" || echo "verify: FAILED"
exit $rc
