#!/usr/bin/env bash
# Static checks of the JAR: listing, Main-Class, the class loads. Nothing is executed.
f="$1"
[ -f "$f" ] || { echo "usage: $0 <demo.jar>"; exit 1; }
rc=0

echo "== file(1)"
file -b "$f"

echo; echo "== unzip -t (exit code 1 is only a warning: the MSI bytes in front of the JAR)"
unzip -tq "$f"; [ $? -le 1 ] || rc=1

echo; echo "== manifest"
main=$(unzip -p "$f" META-INF/MANIFEST.MF | tr -d '\r' | sed -n 's/^Main-Class: //p')
echo "Main-Class: $main"
[ "$main" = "Demo" ] || { echo "FAIL: Main-Class is not Demo"; rc=1; }

echo; echo "== javap (reads the class from the JAR, does not run it)"
if command -v javap >/dev/null; then
    javap -cp "$f" "$main" | grep -F "public static void main" || { echo "FAIL: no main()"; rc=1; }
else
    echo "skipped: javap not installed"
fi

echo; [ $rc -eq 0 ] && echo "verify: OK" || echo "verify: FAILED"
exit $rc
