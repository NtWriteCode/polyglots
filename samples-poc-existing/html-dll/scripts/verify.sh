#!/usr/bin/env bash
# Checks both sides: the PE still loads and runs, the HTML is intact. Exits non-zero on failure.
# Tools that are missing are skipped with a message.
set -euo pipefail
f="$1"; page="$2"
[ -f "$f" ] && [ -f "$page" ] || { echo "usage: $0 <polyglot> <page.html>"; exit 1; }
here=$(dirname "$0")
msg="This came from the DLL side of the polyglot"

echo "== file(1)"
file -b "$f"

echo; echo "== PE headers, export table, overlay"
python3 "$here/check_pe.py" "$f" "$page"

echo; echo "== wine rundll32 $f,Run"
if command -v wine >/dev/null; then
    # No DISPLAY: the MessageBox fails at once and stdout still carries the text.
    out=$(WINEDEBUG=-all DISPLAY= timeout 30 wine rundll32 "$f",Run 2>&1 || true)
    echo "$out"
    grep -qF "$msg" <<<"$out" || { echo "FAIL: rundll32 did not print the DLL message"; exit 1; }
else
    echo "skipped: wine not installed"
fi

echo; echo "== pefile in the REMnux container"
if command -v docker >/dev/null && docker image inspect am-lab-remnux:latest >/dev/null 2>&1; then
    docker run --rm --pull=never -v "$PWD:/work:ro" -w /work --entrypoint sh am-lab-remnux:latest -c \
        'python3 -c "import pefile; p=pefile.PE(\"'"$f"'\"); print([e.name for e in p.DIRECTORY_ENTRY_EXPORT.symbols]); print(hex(p.get_overlay_data_start_offset()))"'
else
    echo "skipped: docker or the am-lab-remnux:latest image is missing"
fi
