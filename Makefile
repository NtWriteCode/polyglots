# Runs the same target in every POC: make [all|build|verify|clean], or make -C <poc> <target>.
# Keeps going past a failing POC and lists the failures at the end.
POCS := $(patsubst %/Makefile,%,$(sort $(wildcard samples-*/*/Makefile)))

.PHONY: all build verify clean list venv

all build verify: venv
all build verify clean:
	@failed=""; \
	for d in $(POCS); do \
		echo; echo "==> $$d: make $@"; \
		$(MAKE) --no-print-directory -C $$d $@ || failed="$$failed $$d"; \
	done; \
	echo; \
	if [ -n "$$failed" ]; then echo "FAILED:$$failed"; exit 1; else echo "all POCs: make $@ OK"; fi

list:
	@printf '%s\n' $(POCS)

# --system-site-packages: the BMP/GIF POCs render with the system Pillow, and their bytes
# depend on its version and fonts. The venv only adds what the ISO/VHD POCs need.
venv: .venv/.installed

.venv/.installed: requirements.txt
	python3 -m venv --system-site-packages .venv
	.venv/bin/pip install -q -r requirements.txt
	touch $@
