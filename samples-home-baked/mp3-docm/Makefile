# MP3 + Word DOCM polyglot. out/polyglot.mp3 is the same bytes with the audio extension.
include ../../poc.mk

AUDIO    := input/audio.mp3
DOCUMENT := input/document.docm
TARGET   := $(OUT)/polyglot.docm
AS_MP3   := $(OUT)/polyglot.mp3

build: $(TARGET) $(AS_MP3)

$(TARGET): $(AUDIO) $(DOCUMENT) scripts/build_v2.py scripts/zip_offset.py | $(OUT)
	$(PY) scripts/build_v2.py --mp3 $(AUDIO) --docm $(DOCUMENT) --out $@

$(AS_MP3): $(TARGET)
	cp $< $@

verify: build
	$(PY) scripts/verify_v2.py $(TARGET)

inputs:
	@echo "Nothing to generate: both files in input/ are the originals."
