#!/usr/bin/env bash
# Static checks of both sides. Nothing is executed: the JAR side is checked with javap only.
f="$1"; main="$2"
[ -f "$f" ] && [ -n "$main" ] || { echo "usage: $0 <polyglot.epub> <expected Main-Class>"; exit 1; }
rc=0

echo "== file(1)"
file -b "$f"

echo; echo "== unzip -t"
unzip -tq "$f" || rc=1

echo; echo "== EPUB side: mimetype first and stored, container.xml present"
python3 - "$f" <<'PY' || rc=1
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
first = z.infolist()[0]
ok = (first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED
      and z.read("mimetype") == b"application/epub+zip"
      and "META-INF/container.xml" in z.namelist())
print(f"first entry {first.filename!r}, stored={first.compress_type == zipfile.ZIP_STORED}, "
      f"container.xml={'META-INF/container.xml' in z.namelist()}, {len(z.namelist())} entries")
sys.exit(0 if ok else 1)
PY

echo; echo "== JAR side: manifest"
got=$(unzip -p "$f" META-INF/MANIFEST.MF | tr -d '\r' | sed -n 's/^Main-Class: //p')
echo "Main-Class: $got"
[ "$got" = "$main" ] || { echo "FAIL: expected Main-Class $main"; rc=1; }

echo; echo "== JAR side: javap (reads the class from the file, does not run it)"
if command -v javap >/dev/null; then
    javap -cp "$f" "$main" | grep -F "public static void main" || { echo "FAIL: no main()"; rc=1; }
else
    echo "skipped: javap not installed"
fi

echo; [ $rc -eq 0 ] && echo "verify: OK" || echo "verify: FAILED"
exit $rc
