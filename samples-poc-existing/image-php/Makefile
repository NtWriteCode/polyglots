# GIF + PHP polyglot (AhnLab ASEC, Dec 2020).
include ../../poc.mk

IMAGE  := input/image.gif
SCRIPT := input/script.php
TARGET := $(OUT)/avatar.gif

build: $(TARGET)

$(TARGET): $(IMAGE) $(SCRIPT) scripts/build.py | $(OUT)
	$(PY) scripts/build.py --gif $(IMAGE) --php $(SCRIPT) --out $@

verify: build
	./scripts/verify.sh $(TARGET) $(IMAGE) $(SCRIPT)

# script.php is hand-written; only the picture is generated.
inputs:
	$(PY) scripts/draw_gif.py --out $(IMAGE)
