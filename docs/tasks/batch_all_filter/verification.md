# Verification Plan: Batch Selection With --all And --filter

## Purpose

Proves that `--all` and `--filter` work on `test`, `show`, `delete`, `move`, that `list` and `export` honour `--filter`, that `--name` behaviour is unchanged, and that docs and version are updated.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
make unit
make check
make integration
```

Expected: all pass. Integration needs SQLcl; `make sqlcl` downloads it once.

## Post-Implementation Verification

### Per-Phase Verification

#### Phase 1: Selector And Matcher

Requirements: REQ-1, REQ-2, REQ-3

```bash
make unit PYTEST_ARGS=tests/test_cli.py
```

Expected: selector and matcher tests pass; zero or two selectors exit 2.

#### Phase 2: Batch Runner And Command Wiring

Requirements: REQ-4, REQ-5, REQ-6

```bash
make unit PYTEST_ARGS=tests/test_cli.py
make integration PYTEST_ARGS=tests/integration/test_batch_compat.py
```

Expected: unit and integration pass; a mocked failure yields `[FAIL]` line, summary and exit 1.

#### Phase 3: list And export Filter

Requirements: REQ-2, REQ-6

```bash
make unit PYTEST_ARGS=tests/test_cli.py
```

Expected: `list --filter` and `export --filter` outputs contain only matching names.

#### Phase 4: Documentation And Version Bump

Requirements: REQ-7, REQ-8

```bash
uv lock --check
uv tool install --from . sqlcl-conn-mng --reinstall
sqlcl-conn-mng --version
npx markdownlint-cli2 README.md ".claude/skills/sqlcl-conn-mng/SKILL.md" "docs/tasks/batch_all_filter/*.md"
```

Expected: lock consistent, `--version` prints `sqlcl-conn-mng 0.3.0`, zero lint errors. Run the linter from the repository root so `.markdownlint-cli2.jsonc` is found.

### Linter

```bash
make check
```

Expected: ruff check, ruff format check and mypy clean.

### Regression Check

```bash
make unit
make integration
```

Expected: all pass.

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [x] AC-1 - zero or multiple selectors exit 2 on the four commands - verified by: Phase 1 unit tests
- [ ] AC-2 - `--name` output and exit codes unchanged - verified by: Phase 1 and 2 unit tests, regression check
- [x] AC-3 - `--filter` is a case-sensitive sorted glob on names - verified by: Phase 1 unit tests
- [x] AC-4 - `--all` selects every connection - verified by: Phase 1 unit tests
- [ ] AC-5 - batch continues after failure, prints lines and summary, exit 1 - verified by: Phase 2 unit tests
- [ ] AC-6 - empty selection exits 1 with `No connections match` - verified by: Phase 2 unit tests
- [ ] AC-7 - batch delete needs `--yes` and lists names first - verified by: Phase 2 unit tests and integration test
- [ ] AC-8 - batch `show` JSON list and table blocks - verified by: Phase 2 unit tests
- [ ] AC-9 - batch `test` and `move` act on each selected connection - verified by: Phase 2 unit and integration tests
- [ ] AC-10 - `list --filter` and `export --filter` narrow output - verified by: Phase 3 unit tests
- [ ] AC-11 - README and SKILL.md document the parameters - verified by: Phase 4 review and markdown lint
- [ ] AC-12 - version `0.3.0` in `pyproject.toml`, `uv.lock` and installed tool - verified by: Phase 4 commands
- [ ] AC-13 - `make check`, `make unit`, `make integration` pass - verified by: Linter and Regression Check sections
