# Makefile for Sphinx documentation with i18n support

# You can set these variables from the command line.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SPHINXINTL    ?= sphinx-intl
SOURCEDIR     = .
BUILDDIR      = _build
LOCALEDIR     = locale

# Default language
LANG          ?= fr

.PHONY: help clean html gettext update-po build-fr build-all

help:
	@echo "GatheRing Documentation Build Commands"
	@echo "======================================="
	@echo ""
	@echo "  make html       - Build HTML documentation (English)"
	@echo "  make gettext    - Extract translatable strings to .pot files"
	@echo "  make update-po  - Update .po files from .pot files"
	@echo "  make build-fr   - Build French documentation"
	@echo "  make build-all  - Build documentation for all languages"
	@echo "  make clean      - Remove build directory"
	@echo ""
	@echo "Translation Workflow:"
	@echo "  1. make gettext   - Extract strings"
	@echo "  2. make update-po - Create/update .po files"
	@echo "  3. Edit locale/fr/LC_MESSAGES/*.po files"
	@echo "  4. make build-fr  - Build translated docs"
	@echo ""

clean:
	rm -rf $(BUILDDIR)

html:
	$(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html $(SPHINXOPTS)
	@echo ""
	@echo "Build finished. Open $(BUILDDIR)/html/index.html"

# Extract translatable strings to .pot files
gettext:
	$(SPHINXBUILD) -b gettext $(SOURCEDIR) $(BUILDDIR)/gettext $(SPHINXOPTS)
	@echo ""
	@echo "Gettext catalog files generated in $(BUILDDIR)/gettext/"

# Update .po files from .pot files
update-po:
	$(SPHINXINTL) update -p $(BUILDDIR)/gettext -l $(LANG)
	@echo ""
	@echo "Translation files updated in $(LOCALEDIR)/$(LANG)/LC_MESSAGES/"

# Build French documentation
build-fr:
	$(SPHINXBUILD) -b html -D language=fr $(SOURCEDIR) $(BUILDDIR)/html/fr $(SPHINXOPTS)
	@echo ""
	@echo "French documentation built. Open $(BUILDDIR)/html/fr/index.html"

# Build all languages
build-all: html build-fr
	@echo ""
	@echo "All documentation built:"
	@echo "  - English: $(BUILDDIR)/html/index.html"
	@echo "  - French:  $(BUILDDIR)/html/fr/index.html"
