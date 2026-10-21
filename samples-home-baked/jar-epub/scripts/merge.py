#!/usr/bin/env python3
import zipfile, sys, os

def merge(jar, epub, out):
    seen = set()
    entries = []

    # JAR entries first so MANIFEST.MF is never overwritten by epub's META-INF
    for path in [jar, epub]:
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.filename not in seen:
                    seen.add(info.filename)
                    entries.append((path, info))

    # EPUB spec: mimetype must be the first entry and uncompressed
    entries.sort(key=lambda x: (x[1].filename != 'mimetype'))

    with zipfile.ZipFile(out, 'w') as zout:
        for src, info in entries:
            with zipfile.ZipFile(src) as zf:
                data = zf.read(info.filename)
            if info.filename == 'mimetype':
                info.compress_type = zipfile.ZIP_STORED
            zout.writestr(info, data)

    print(f"Created {out}")
    print(f"  Rename to .jar  -> runs as Java application")
    print(f"  Rename to .epub -> opens as ebook")

if __name__ == '__main__':
    jar  = sys.argv[1] if len(sys.argv) > 1 else 'hello.jar'
    epub = sys.argv[2] if len(sys.argv) > 2 else 'book.epub'
    out  = sys.argv[3] if len(sys.argv) > 3 else 'polyglot.jar'
    merge(jar, epub, out)
