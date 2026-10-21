# EXE + ZIP polyglot: the files in input/zip/ are zipped into the EXE's overlay.
include ../../poc.mk

PROGRAM := input/program.exe
FILES   := $(wildcard input/zip/*)
TARGET  := $(OUT)/polyglot.exe

build: $(TARGET)

$(TARGET): $(PROGRAM) $(FILES) scripts/build_polyglot.py | $(OUT)
	$(PY) scripts/build_polyglot.py --pe $(PROGRAM) --payload input/zip --out $@

verify: build
	$(PY) scripts/verify_polyglot.py $(TARGET)

# The files in input/zip/ are hand-written; only the EXE is compiled.
inputs:
	$(CC) -Os -s -o $(PROGRAM) src/hello.c
