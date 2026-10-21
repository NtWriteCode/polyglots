#!/usr/bin/env bash
# Shows what each reader makes of the file: image tools see a GIF, PHP runs the comment.
f="$1"; clean="$2"; php="$3"
[ -f "$f" ] && [ -f "$clean" ] && [ -f "$php" ] || { echo "usage: $0 <polyglot.gif> <clean.gif> <payload.php>"; exit 1; }
fail=0

echo "== file(1)"
file -b "$f"

echo; echo "== GIF blocks + Pillow pixel compare"
python3 scripts/check_gif.py "$f" "$clean" "$php" || fail=1

echo; echo "== ImageMagick identify (host)"
if command -v identify >/dev/null; then
  identify "$f" || fail=1
  echo "comment: $(identify -format '%c' "$f")"
else
  echo "skipped: identify not installed"
fi

echo; echo "== php"
if command -v php >/dev/null; then
  php "$f" | grep -a "PHP side" || fail=1
else
  echo "skipped: php not installed; try: docker run --rm -v \"\$PWD/out:/w:ro\" php:cli php /w/$(basename "$f")"
fi

echo; echo "== REMnux container (exiftool + identify)"
if command -v docker >/dev/null && docker image inspect am-lab-remnux:latest >/dev/null 2>&1; then
  docker run --rm -v "$PWD:/work:ro" -w /work --entrypoint sh am-lab-remnux:latest \
    -c "exiftool $f | grep -E 'File Type |GIF Version|Image Size|Comment'; identify $f" || fail=1
else
  echo "skipped: docker or the am-lab-remnux:latest image is not available"
fi

echo
[ "$fail" = 0 ] && echo "verify: OK" || { echo "verify: FAILED"; exit 1; }
