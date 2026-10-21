# JPEG + ISO polyglot: the picture sits in the ISO's unused first 32 KiB.
include ../../poc.mk

IMAGE  := input/cover.jpg
LNK    := input/payload.lnk
TARGET := $(OUT)/polyglot.iso

build: $(TARGET)

$(TARGET): $(IMAGE) $(LNK) scripts/build_v3.py | $(OUT)
	$(PY) scripts/build_v3.py --jpg $(IMAGE) --lnk $(LNK) --out $@

verify: build
	$(PY) scripts/verify_v3.py $(TARGET)

# cover.jpg is a plain picture; only the shortcut is generated.
inputs:
	$(PY) scripts/build_lnk.py --out $(LNK)
