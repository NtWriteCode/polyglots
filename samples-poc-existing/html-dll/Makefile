# HTML + DLL polyglot (StrelaStealer: DCSO Nov 2022, Unit 42 Mar 2024).
include ../../poc.mk

DLL    := input/payload.dll
PAGE   := input/page.html
TARGET := $(OUT)/polyglot.html

build: $(TARGET)

$(TARGET): $(DLL) $(PAGE) scripts/build_polyglot.py scripts/pe.py | $(OUT)
	$(PY) scripts/build_polyglot.py $(DLL) $(PAGE) --out $@

verify: build
	./scripts/verify.sh $(TARGET) $(PAGE)

# page.html is hand-written; only the DLL is compiled.
inputs:
	$(CC) -shared -Os -s -o $(DLL) src/payload.c
