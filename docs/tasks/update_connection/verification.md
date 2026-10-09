# Verification Plan: Update Command For Saved Connections

## Purpose

Proves that `update` changes the name, user, connect string and password of one saved connection, alone or combined, without touching anything else, and that docs and version are updated.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
make check
make unit
make integration
```

Expected: all pass. Integration needs SQLcl (`make sqlcl` downloads it once); the saved-password scenarios skip without the database variables.

## Post-Implementation Verification

### Per-Phase Verification

#### Phase 1: Discovery Of SQLcl Replace Behavior

Requirements: REQ-4

Read `open_questions.md`, Q2. Expected: it records the observed effect of `connect -save -replace` with a changed user and connect string, and of a failed connect, with no password in the text.

#### Phase 2: Properties Writer

Requirements: REQ-2

```bash
make unit PYTEST_ARGS="tests/test_properties.py tests/test_store.py"
```

Expected: pass.

#### Phase 3: Update Command

Requirements: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5

```bash
make unit PYTEST_ARGS=tests/test_cli.py
```

Expected: pass.

#### Phase 4: Integration, Docs And Version

Requirements: REQ-2, REQ-3, REQ-6, REQ-7

```bash
make integration PYTEST_ARGS=tests/integration/test_update_compat.py
uv tool install --from . sqlcl-conn-mng --reinstall
sqlcl-conn-mng --version
```

Expected: pass; the version prints `0.4.0`.

### Linter

```bash
make check
markdownlint-cli2 README.md ".claude/skills/sqlcl-conn-mng/SKILL.md" "docs/tasks/update_connection/*.md"
```

Run `markdownlint-cli2` from the repository root so it finds `.markdownlint-cli2.jsonc`.

### Regression Check

```bash
make unit
make integration
```

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [x] AC-1 - option rules and errors - verified by: Phase 3 verification, `tests/test_cli.py`
- [x] AC-2 - metadata-only update touches one value and no SQLcl process starts - verified by: Phase 2 and Phase 3 verification
- [ ] AC-3 - SQLcl `connmgr show` reads the Python-written values - verified by: Phase 4 verification, `tests/integration/test_update_compat.py`
- [ ] AC-4 - password-only update keeps the id and saves the password - verified by: Phase 3 and Phase 4 verification
- [ ] AC-5 - `--no-save-password` and `--prompt-password` - verified by: Phase 3 and Phase 4 verification
- [x] AC-6 - failed connect and refused inputs leave the store unchanged - verified by: Phase 3 verification
- [x] AC-7 - combined update applies all changes in order - verified by: Phase 3 verification
- [x] AC-8 - no password in output, logs or the SQLcl argument list - verified by: Phase 3 verification
- [ ] AC-9 - README, SKILL.md and version updated - verified by: Phase 4 verification, `sqlcl-conn-mng --version`
- [ ] AC-10 - `make check`, `make unit`, `make integration` pass - verified by: Linter and Regression Check sections
