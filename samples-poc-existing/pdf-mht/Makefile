# PDF + Word MHT polyglot, "MalDoc in PDF" (JPCERT/CC, Aug 2023).
include ../../poc.mk

PDF    := input/document.pdf
MHT    := input/document.mht
TARGET := $(OUT)/invoice.pdf

build: $(TARGET)

$(TARGET): $(PDF) $(MHT) | $(OUT)
	cat $(PDF) $(MHT) > $@

verify: build
	./scripts/verify.sh $(TARGET)

inputs:
	$(PY) scripts/make_inputs.py --pdf $(PDF) --mht $(MHT)
