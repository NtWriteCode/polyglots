# JPEG + VHD polyglot: a picture at the start, a FAT16 disk with the shortcut, a VHD footer.
include ../../poc.mk

IMAGE  := input/cover.jpg
LNK    := input/payload.lnk
FAT    := $(WORK)/payload.fat
TARGET := $(OUT)/polyglot.vhd

build: $(TARGET)

$(FAT): $(LNK) scripts/build_fat.py | $(WORK)
	$(PY) scripts/build_fat.py --payload $(LNK) --out $@

$(TARGET): $(IMAGE) $(FAT) scripts/build_v4.py | $(OUT)
	$(PY) scripts/build_v4.py --jpg $(IMAGE) --fat $(FAT) --out $@

verify: build
	$(PY) scripts/verify_v4.py $(TARGET)

# cover.jpg is a plain picture; only the shortcut is generated.
inputs:
	$(PY) scripts/build_lnk.py --out $(LNK)
