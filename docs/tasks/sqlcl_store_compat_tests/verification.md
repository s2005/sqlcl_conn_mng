# Verification Plan: Integration Tests for Compatibility with SQLcl-Made Store Entries

## Purpose

Prove that the new `tests/integration/` package covers every requirement in `PRD.md`, runs against real SQLcl 25.4.1, skips cleanly without SQLcl or without a database, leaves the default unit run unchanged, never exposes the database password or a real store, and runs the same way locally and in GitHub Actions through the `make` targets.

All commands run from `<repo-root>` in Git Bash. `<scratch-root>` is the session scratch directory. Before the `Makefile` exists (Pre-Implementation), the underlying `uv run` commands are used; afterwards only `make` targets are.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
uv run pytest -q
```

Expected: all pass; baseline on 2026-10-08 was `93 passed, 1 deselected`.

### Existing Integration Test Passes

```bash
uv run pytest -m integration -q
```

Expected: `1 passed, 93 deselected`, with `sql.exe` found on `PATH`.

### Existing Lint Is Clean

```bash
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy
```

Expected: clean, as on 2026-10-08, so the new `check` target and the workflow start green.

### Store Marker

```bash
touch <scratch-root>/store_marker
```

Expected: no output. The marker dates the start of the task for the store check in "Secret and Store Hygiene".

## Post-Implementation Verification

### Per-Phase Verification

#### Phase 1: Harness, Make Targets and Import Fixture Discovery

REQ-1, REQ-8, REQ-10.

```bash
make check
make unit
make sqlcl && make sqlcl
make integration PYTEST_ARGS=tests/integration/test_harness_smoke.py
SQLCL_BIN=/nonexistent/sql.exe PATH="$(printf %s "$PATH" | tr ':' '\n' | grep -vi sqlcl | paste -sd: -)" make integration PYTEST_ARGS=tests/integration
```

Expected: `check` clean; `unit` at the baseline pass count with no integration test selected; the first `sqlcl` downloads and unpacks, the second does nothing; the smoke tests pass; the last command reports every test skipped and none failed. `open_questions.md`, Q11 records the accepted export or the rejection and the fallback taken.

#### Phase 2: Folder and Import Scenarios

REQ-2, REQ-3.

```bash
make integration PYTEST_ARGS="tests/integration/test_folders_compat.py tests/integration/test_import_compat.py"
```

Expected: all pass.

#### Phase 3: Connection Operations and Edge-Case Values

REQ-4, REQ-5.

```bash
make integration PYTEST_ARGS="tests/integration/test_connection_ops_compat.py tests/integration/test_edge_values_compat.py"
```

Expected: all pass, or a strict `xfail` limited to Windows whose reason names a follow-up task.

#### Phase 4: Live-Database Scenarios

REQ-6, REQ-8, REQ-10. The password file holds a dummy value only; the variable is set without printing it.

```bash
env -u SQLCL_ITEST_PASSWORD make db-start; echo "exit $?"
export SQLCL_ITEST_PASSWORD="$(tr -d '[:space:]' < <scratch-root>/itest_password)"
[ -n "$SQLCL_ITEST_PASSWORD" ] || { echo "no password read - aborting"; exit 1; }
make db-start 2>&1 | grep -cF "$SQLCL_ITEST_PASSWORD"
make integration PYTEST_ARGS=tests/integration/test_saved_password_compat.py
make db-stop
env -u SQLCL_ITEST_PASSWORD make integration PYTEST_ARGS=tests/integration/test_saved_password_compat.py
```

Expected: the first command fails with `SQLCL_ITEST_PASSWORD is not set` and a non-zero exit; the `grep -c` prints `0` (make echoed no password); the database scenarios pass; `db-stop` removes the container; the last run reports every test skipped with `SQLCL_ITEST_PASSWORD` named as missing.

#### Phase 5: Format Conformance

REQ-7.

```bash
make integration PYTEST_ARGS=tests/integration/test_format_conformance.py
```

Expected: all pass, including the self-test that a failing format assertion names the SQLcl release; database-dependent checks skip without the password variable.

#### Phase 6: GitHub Actions Workflow

REQ-11, REQ-10.

```bash
grep -nE "25\.4\.1|oracle-xe|XEPDB1|1521|itest|ruff|pytest|mypy" .github/workflows/ci.yml; echo "exit $?"
git push origin HEAD
RUN_ID=$(gh run list --branch "$(git branch --show-current)" --workflow ci.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status; echo "exit $?"
gh run view "$RUN_ID" --json jobs --jq '.jobs[] | {name, conclusion}'
gh run view "$RUN_ID" --log | grep -E "SKIPPED|skipped" | grep -c "SQLCL_ITEST_"
gh run rerun "$RUN_ID" && gh run watch "$RUN_ID" --exit-status
gh run view "$RUN_ID" --log | grep -ciE "cache restored|cache hit"
```

Expected: the `grep` over the workflow prints only `exit 1` (no duplicated command or setting); the run exits 0; both matrix jobs report `success`; the skip count is non-zero and comes from the Windows job only; the rerun is green and its log reports the SQLcl cache restored. The Ubuntu job log shows the password only as `***`.

#### Phase 7: Documentation and Final Verification

REQ-9, REQ-8.

```bash
markdownlint-cli2 README.md "docs/tasks/sqlcl_store_compat_tests/*.md"
```

Expected: `0 issues`, using the repository's own `.markdownlint-cli2.jsonc`. `README.md`, "Development" and "Testing" name the `make` targets, the three `SQLCL_ITEST_*` variables, `db-start` / `db-stop`, the workflow, and the `sql.exe` requirement for `SQLCL_BIN` on Windows, without repeating the commands behind the targets.

### Secret and Store Hygiene

REQ-8. Run with `SQLCL_ITEST_PASSWORD` set as in Phase 4.

```bash
[ -n "$SQLCL_ITEST_PASSWORD" ] || { echo "no password set - aborting"; exit 1; }
git grep -IlF --untracked -e "$SQLCL_ITEST_PASSWORD"; echo "exit $?"
find .sqlcl -newer <scratch-root>/store_marker 2>/dev/null | wc -l
grep -rnE "open\(|read_bytes|read_text" tests/integration | grep -ci "sso"
git ls-files | grep -ciE "\.sso$|^\.cache/"
```

Expected: the second command prints only `exit 1` (no file holds the password); the third prints `0` (the repository store did not change); the fourth and fifth print `0` (no test opens a wallet; no wallet and no SQLcl download is tracked). The commands print counts and file names only, never contents.

### Linter

```bash
make check
```

Expected: `ruff check`, `ruff format --check` and `mypy` all clean.

### Regression Check

```bash
make unit
make integration
```

Expected: the unit run matches the baseline pass count and selects no integration test; the integration run passes, with strict `xfail` only where a follow-up task is named, and the database scenarios pass or skip depending on `SQLCL_ITEST_PASSWORD`.

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [ ] AC-1 - the new package runs with SQLcl, skips without it, and the default run selects no integration test - verified by: Phase 1 verification
- [ ] AC-2 - the import fixture is committed and SQLcl imports it - verified by: Phase 1 verification and `open_questions.md`, Q11
- [ ] AC-3 - folder scenarios pass, including the tool's folder commands on SQLcl-built trees - verified by: Phase 2 verification
- [ ] AC-4 - import scenarios pass, including `RENAME` and `REPLACE`, with no imported value lost - verified by: Phase 2 verification
- [ ] AC-5 - connection operation scenarios pass for SQLcl-made and tool-made operations, including case-sensitive lookup - verified by: Phase 3 verification
- [ ] AC-6 - every edge-case value is reported exactly or is a strict, platform-limited `xfail` naming its follow-up - verified by: Phase 3 verification
- [ ] AC-7 - database scenarios pass with the variables set and skip with a reason without them - verified by: Phase 4 verification
- [ ] AC-8 - format conformance passes on SQLcl 25.4.1 and a failing assertion names the release - verified by: Phase 5 verification
- [ ] AC-9 - no password in tool output or committed files, the repository store unchanged, no wallet opened - verified by: "Secret and Store Hygiene" and the `assert_no_password` checks in Phase 4
- [ ] AC-10 - `README.md` documents the targets, variables, database targets, workflow and `sql.exe` note without repeating commands, and markdown lint is clean - verified by: Phase 7 verification
- [ ] AC-11 - ruff check and format pass, the unit suite passes, and every `xfail` is strict, names a follow-up and is platform-limited - verified by: "Linter" and "Regression Check"
- [ ] AC-12 - every `make` target works locally, `db-start` refuses without the password and never echoes it, and no target's command or setting is repeated elsewhere - verified by: Phase 1, Phase 4 and Phase 6 verification
- [ ] AC-13 - the workflow is green on Ubuntu and Windows, database scenarios run on Ubuntu and skip on Windows, the password is masked, and a rerun hits the SQLcl cache - verified by: Phase 6 verification
