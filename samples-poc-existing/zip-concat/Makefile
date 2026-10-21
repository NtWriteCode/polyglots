# Two ZIPs glued together (Perception Point, Nov 2024).
include ../../poc.mk

FIRST  := input/decoy.zip
SECOND := input/payload.zip
TARGET := $(OUT)/SHIPPING_INV_PL_BL_pdf.zip

build: $(TARGET)

$(TARGET): $(FIRST) $(SECOND) scripts/concat.py | $(OUT)
	$(PY) scripts/concat.py $(FIRST) $(SECOND) --out $@

verify: build
	./scripts/verify.sh $(TARGET)

inputs:
	$(PY) scripts/build_parts.py --out input
