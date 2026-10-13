# Verification Plan: Copy Saved Connections Between Homes

## Purpose

Covers the `copy` subcommand: the opaque directory copy under a new id, folder placement in the target through SQLcl, name-clash and same-home refusals, batch and JSON output, SQLcl acceptance of the copied password, documentation, and the 0.6.0 version bump.

## Pre-Implementation Verification

Run from `<repo-root>`.

### Existing Tests Pass

```bash
make check
make unit
```

Expected: both pass.

### Baseline Version

```bash
sqlcl-conn-mng --version
```

Expected: 0.5.0.

## Post-Implementation Verification

### Per-Phase Verification

#### Phase 1: Store copy primitive

Covers REQ-2.

```bash
uv run pytest -q tests/test_store.py
```

Expected: all pass, including the byte-identical copy, the id shape and uniqueness, the copy without a wallet, target creation, staging cleanup and source-unchanged tests.

#### Phase 2: `copy` subcommand

Covers REQ-1, REQ-3, REQ-4, REQ-5.

```bash
uv run pytest -q tests/test_cli.py -k copy
uv run sqlcl-conn-mng copy --help
```

Expected: tests pass, and the help lists `--to-home`, `--name`, `--filter`, `--all` and `--format`.

#### Phase 3: SQLcl acceptance test

Covers REQ-2, REQ-3.

```bash
read -rs SQLCL_ITEST_PASSWORD && export SQLCL_ITEST_PASSWORD
make db-start
make integration PYTEST_ARGS="-k copy"
make db-stop
```

Expected: the copy test passes. Without `SQLCL_ITEST_PASSWORD` it skips and names the missing variables.

#### Phase 4: Documentation and version

Covers REQ-6, REQ-7.

```bash
npx markdownlint-cli2 README.md .claude/skills/sqlcl-conn-mng/SKILL.md "docs/tasks/copy_between_homes/*.md"
grep -n '^version' pyproject.toml
uv tool install --from . sqlcl-conn-mng --reinstall
sqlcl-conn-mng --version
```

Expected: no lint errors, `version = "0.6.0"`, and `--version` prints 0.6.0.

### Linter

```bash
make check
```

Expected: ruff check, ruff format check and mypy are clean.

### Regression Check

```bash
make unit
make integration
```

Expected: all unit tests pass. The integration tests pass or skip with a reason, as before.

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [ ] AC-1 - `copy --help` lists the options; a missing `--to-home`, a missing selector or two selectors exit with code 2 - verified by: Phase 2 tests and `copy --help`
- [ ] AC-2 - JSON single and batch envelopes; a batch with no match exits with code 1 - verified by: Phase 2 tests
- [x] AC-3 - New 22-character id, distinct from source and target ids; files byte-identical; copy without a wallet when the source has none - verified by: Phase 1 tests
- [ ] AC-4 - Missing target home created; source unchanged; no staging directory left after a failure - verified by: Phase 1 and Phase 2 tests
- [ ] AC-5 - Root copy runs no SQLcl; nested copy runs `add -folder` only when missing, then `move`, against the target home; folder failure rolls back - verified by: Phase 2 tests
- [ ] AC-6 - Real SQLcl reports the copied password as saved and the copy in its folder path - verified by: Phase 3
- [ ] AC-7 - A case-insensitive name clash gives `[FAIL]`, the rest are copied, exit code 1, the target connection is unchanged - verified by: Phase 2 tests
- [ ] AC-8 - Same home exits with code 1 with nothing written; a duplicate-name batch exits with code 1 with nothing copied; an unknown `--name` exits with code 1 - verified by: Phase 2 tests
- [ ] AC-9 - README and SKILL.md document `copy` per REQ-6 with no move tip, lint clean - verified by: Phase 4 lint and review
- [ ] AC-10 - Version 0.6.0 in `pyproject.toml` and `uv.lock`; global `--version` prints 0.6.0 - verified by: Phase 4 commands
