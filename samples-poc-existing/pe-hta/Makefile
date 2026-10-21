# EXE + HTA polyglot (Emmenhtal 2024, ClickFix/Lumma 2025).
include ../../poc.mk

PROGRAM := input/program.exe
SCRIPT  := input/script.hta
TARGET  := $(OUT)/polyglot.exe

build: $(TARGET)

$(TARGET): $(PROGRAM) $(SCRIPT) scripts/build_polyglot.py | $(OUT)
	$(PY) scripts/build_polyglot.py $(PROGRAM) $(SCRIPT) --out $@

verify: build
	./scripts/verify.sh $(TARGET) $(SCRIPT)

# script.hta is hand-written; only the EXE is compiled.
inputs:
	$(CC) -Os -s -o $(PROGRAM) src/hello.c
