SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

SQLCL_VERSION ?= 25.4.1.022.0618
SQLCL_URL := https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-$(SQLCL_VERSION).zip
SQLCL_DIR := .cache/sqlcl
SQLCL_HOME := $(SQLCL_DIR)/$(SQLCL_VERSION)
SQLCL_BIN_DIR := $(SQLCL_HOME)/sqlcl/bin
PYTEST_ARGS ?=

ENGINE ?= podman
DB_IMAGE := docker.io/gvenzl/oracle-xe:21-slim
DB_CONTAINER := sqlcl-itest-xe
DB_PORT ?= 1521
DB_WAIT_TRIES ?= 120
DB_WAIT_SECONDS ?= 5
SQLCL_ITEST_USER ?= itest
SQLCL_ITEST_CONNECT ?= //localhost:$(DB_PORT)/XEPDB1
export SQLCL_ITEST_USER SQLCL_ITEST_CONNECT

.PHONY: check unit integration sqlcl print-sqlcl-version print-sqlcl-dir print-sqlcl-bin db-start db-stop

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

# Start the Oracle XE test container and wait until it is healthy.
# Needs SQLCL_ITEST_PASSWORD in the environment; it is passed by name only.
db-start:
	if [ -z "$${SQLCL_ITEST_PASSWORD:-}" ]; then echo "SQLCL_ITEST_PASSWORD is not set" >&2; exit 1; fi; \
	ORA_PW="$$(uv run python -c "import secrets; print(secrets.token_urlsafe(18))")"; \
	APP_USER="$$SQLCL_ITEST_USER" APP_USER_PASSWORD="$$SQLCL_ITEST_PASSWORD" ORACLE_PASSWORD="$$ORA_PW" $(ENGINE) run -d --name $(DB_CONTAINER) -p $(DB_PORT):1521 -e APP_USER -e APP_USER_PASSWORD -e ORACLE_PASSWORD $(DB_IMAGE) >/dev/null; \
	i=0; \
	while [ "$$i" -lt $(DB_WAIT_TRIES) ]; do \
		if $(ENGINE) exec $(DB_CONTAINER) healthcheck.sh >/dev/null 2>&1; then echo "database ready"; exit 0; fi; \
		i=$$((i + 1)); sleep $(DB_WAIT_SECONDS); \
	done; \
	echo "database not ready after $(DB_WAIT_TRIES) tries" >&2; \
	$(ENGINE) logs --tail 30 $(DB_CONTAINER) 2>&1 | grep -vF -e "$$SQLCL_ITEST_PASSWORD" -e "$$ORA_PW" >&2 || true; \
	exit 1

# Remove the Oracle XE test container; a missing container is ignored.
db-stop:
	-$(ENGINE) rm -f $(DB_CONTAINER)
