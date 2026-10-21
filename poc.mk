# Shared conventions for every POC. Each POC Makefile starts with `include ../../poc.mk`.
#
# Layout of a POC:
#   input/    the parts of the polyglot, one file each. Replace them with your own (same names).
#   out/      the finished polyglot(s), nothing else
#   scripts/  build and verify scripts
#   src/      sources of the demo parts, where they are compiled (C, Java)
#   work/     temporary files of the build
#
# Commands, the same in every POC:
#   make          build + verify
#   make build    build the polyglot(s) from input/ into out/
#   make verify   run the checks against out/ (they expect the demo parts)
#   make inputs   recreate the demo parts in input/ from src/ or scripts/ (overwrites them)
#   make clean    remove out/ and work/ (input/ is never touched)

POC_ROOT := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))

# The shared virtualenv (`make venv` at the top level) goes first on PATH when it exists,
# so `python3` in recipes and verify scripts sees pycdlib/pyfatfs plus the system packages.
VENV := $(POC_ROOT)/.venv
ifneq ($(wildcard $(VENV)/bin/python3),)
export PATH := $(VENV)/bin:$(PATH)
endif
# Verify scripts import the build scripts; keep scripts/ free of __pycache__.
export PYTHONDONTWRITEBYTECODE := 1

PY    := python3
CC    := x86_64-w64-mingw32-gcc
JAVAC := javac
JAR   := jar

OUT   := out
WORK  := work

.PHONY: all build verify inputs clean
.DEFAULT_GOAL := all

all: build verify

$(OUT) $(WORK):
	mkdir -p $@

clean:
	rm -rf $(OUT) $(WORK)
