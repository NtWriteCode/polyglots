# BMP + HTA polyglot (Lazarus, Apr 2021).
include ../../poc.mk

IMAGE  := input/image.bmp
SCRIPT := input/script.hta
TARGET := $(OUT)/polyglot.bmp

build: $(TARGET)

$(TARGET): $(IMAGE) $(SCRIPT) scripts/polyglot.py | $(OUT)
	$(PY) scripts/polyglot.py $(IMAGE) $(SCRIPT) --out $@

verify: build
	./scripts/verify.sh $(TARGET) $(IMAGE) $(SCRIPT)

# script.hta is hand-written; only the picture is generated.
inputs:
	$(PY) scripts/draw_bmp.py --out $(IMAGE)
