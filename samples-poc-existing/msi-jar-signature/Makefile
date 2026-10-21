# MSI + JAR polyglot (CVE-2020-1464). The JAR is appended to the MSI.
# Without input/installer.msi only the JAR is copied to out/demo.jar.
include ../../poc.mk

JARFILE := input/program.jar
MSI     := input/installer.msi
TARGET  := $(if $(wildcard $(MSI)),$(OUT)/polyglot.msi,$(OUT)/demo.jar)

build: $(TARGET)

$(OUT)/polyglot.msi: $(MSI) $(JARFILE) | $(OUT)
	cat $(MSI) $(JARFILE) > $@

$(OUT)/demo.jar: $(JARFILE) | $(OUT)
	cp $(JARFILE) $@

verify: build
	./scripts/verify.sh $(TARGET)

inputs: | $(WORK)
	$(JAVAC) -d $(WORK) src/Demo.java
	$(JAR) cfm $(JARFILE) src/MANIFEST.MF -C $(WORK) Demo.class
