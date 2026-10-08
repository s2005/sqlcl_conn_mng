SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

SQLCL_VERSION ?= 25.4.1.022.0618
SQLCL_URL := https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-$(SQLCL_VERSION).zip
SQLCL_DIR := .cache/sqlcl
SQLCL_HOME := $(SQLCL_DIR)/$(SQLCL_VERSION)
SQLCL_BIN_DIR := $(SQLCL_HOME)/sqlcl/bin
PYTEST_ARGS ?=

.PHONY: check unit integration sqlcl print-sqlcl-version print-sqlcl-dir print-sqlcl-bin

# Lint, format check and type check.
check:
	uv run ruff check src tests scripts
	uv run ruff format --check src tests scripts
	uv run mypy

# Unit tests (integration tests are deselected).
unit:
	uv run pytest -q $(PYTEST_ARGS)

# Integration tests against a real SQLcl.
integration:
	uv run pytest -m integration -q -rs $(PYTEST_ARGS)

# Download and unpack SQLcl $(SQLCL_VERSION) into $(SQLCL_DIR), once.
sqlcl:
	@if [ -d "$(SQLCL_BIN_DIR)" ]; then \
		echo "SQLcl $(SQLCL_VERSION) is already unpacked in $(SQLCL_HOME)"; \
	else \
		mkdir -p "$(SQLCL_DIR)"; \
		curl -fsSL -o "$(SQLCL_HOME).zip" "$(SQLCL_URL)"; \
		rm -rf "$(SQLCL_HOME).tmp"; \
		uv run python -m zipfile -e "$(SQLCL_HOME).zip" "$(SQLCL_HOME).tmp"; \
		chmod +x "$(SQLCL_HOME).tmp/sqlcl/bin/sql"; \
		mv "$(SQLCL_HOME).tmp" "$(SQLCL_HOME)"; \
		rm -f "$(SQLCL_HOME).zip"; \
	fi

# Print the pinned SQLcl version.
print-sqlcl-version:
	@echo "$(SQLCL_VERSION)"

# Print the absolute SQLcl download directory.
print-sqlcl-dir:
	@echo "$(abspath $(SQLCL_DIR))"

# Print the absolute directory holding the sql launcher.
print-sqlcl-bin:
	@echo "$(abspath $(SQLCL_BIN_DIR))"
