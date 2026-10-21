# JAR + EPUB polyglot: one ZIP that is a runnable JAR and an ebook.
include ../../poc.mk

PROGRAM := input/program.jar
BOOK    := input/book.epub
TARGET  := $(OUT)/hertz.epub

# Second pair from an external sample. It ships as external.zip (password "infected", the usual
# convention for malware samples) and the build unpacks it into external/. Nothing runs the JAR.
EXT_ZIP    := external.zip
EXT_JAR    := external/2b127d3989e38dac7f220e082813b65bc355c1cb819ffaddd6b4e6aa2b101dfd.jar
EXT_BOOK   := external/Philipp.Schott-Egy.kisallatrendelo.hetkoznapjai.2020.HUN.EPUB.Ebook-WhoAmI.epub
EXT_TARGET := $(if $(wildcard $(EXT_ZIP) $(EXT_JAR)),$(OUT)/Philipp.Schott.epub)

build: $(TARGET) $(EXT_TARGET)

$(TARGET): $(PROGRAM) $(BOOK) scripts/merge.py | $(OUT)
	$(PY) scripts/merge.py $(PROGRAM) $(BOOK) $@

$(EXT_JAR) $(EXT_BOOK) &: $(EXT_ZIP)
	$(PY) -c "import zipfile; zipfile.ZipFile('$(EXT_ZIP)').extractall(pwd=b'infected')"
	touch $(EXT_JAR) $(EXT_BOOK)

$(OUT)/Philipp.Schott.epub: $(EXT_JAR) $(EXT_BOOK) scripts/merge.py | $(OUT)
	$(PY) scripts/merge.py $(EXT_JAR) $(EXT_BOOK) $@

verify: build
	./scripts/verify.sh $(TARGET) Main
	$(if $(EXT_TARGET),./scripts/verify.sh $(EXT_TARGET) org.example.GUI)

# book.epub is a plain ebook; only the JAR is compiled.
inputs: | $(WORK)
	$(JAVAC) --release 17 -d $(WORK) src/Main.java
	$(JAR) cfm $(PROGRAM) src/MANIFEST.MF -C $(WORK) Main.class
