# ── AGOL Maintenance Scripts ─────────────────────────────────────
#  Converts scripts/*.py → notebooks/*.ipynb using Jupytext
# ─────────────────────────────────────────────────────────────────

SCRIPTS  := $(wildcard scripts/*.py)
NOTEBOOKS := $(patsubst scripts/%.py, notebooks/%.ipynb, $(SCRIPTS))

.PHONY: notebooks clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-18s %s\n", $$1, $$2}'

notebooks: $(NOTEBOOKS) ## Convert all scripts to notebooks
	@echo "✓  $(words $(NOTEBOOKS)) notebook(s) generated."

notebooks/%.ipynb: scripts/%.py
	@mkdir -p notebooks
	jupytext --to ipynb --output $@ $<
	@echo "  → $@"

clean: ## Remove generated notebooks
	rm -f notebooks/*.ipynb
	@echo "✓  Cleaned."
