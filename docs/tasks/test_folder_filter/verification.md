# Verification Plan: Folder Selection For test

## Purpose

Proves that `test --folder` selects the same connections as `list --folder`, combines with `--filter` as AND, enforces the selector rule with exit code 2, reports an empty folder selection as the existing batch error, behaves as a normal batch, leaves `show`, `delete`, `move`, `list` and `export` unchanged, and ships as 0.6.0 with documentation.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
make check
make unit
```

Expected: both clean.

### Baseline Behavior

```bash
uv run sqlcl-conn-mng --version
MSYS_NO_PATHCONV=1 uv run sqlcl-conn-mng test --home .sqlcl --folder /dev
```

Expected: `sqlcl-conn-mng 0.5.0`; the second command is a usage error (exit 2) naming `--folder` as unrecognized or the selector group as required. Today `list --folder /` returns only root-level connections; REQ-8 keeps that. No coverage threshold is configured, so no coverage table is kept.

## Post-Implementation Verification

### Per-Phase Verification

#### Phase 1: test --folder selection

Requirements: REQ-1, REQ-2, REQ-3, REQ-4, REQ-7, REQ-8

```bash
make unit PYTEST_ARGS="tests/test_cli.py -k 'selector or folder or empty_selection or move_batch or root_folder'"
uv run sqlcl-conn-mng test --help
```

Expected: every selected test passes; help lists `--name`, `--all`, `--filter` and `--folder`, with the AND wording on `--filter` and `--folder`.

#### Phase 2: Version and documentation

Requirements: REQ-5, REQ-6

```bash
uv run sqlcl-conn-mng --version
grep -n "0.6.0" pyproject.toml uv.lock .claude/skills/sqlcl-conn-mng/SKILL.md
grep -n -- "test.*--folder" README.md .claude/skills/sqlcl-conn-mng/SKILL.md
```

Expected: `sqlcl-conn-mng 0.6.0`; 0.6.0 present in all three files; `test --folder` documented in both documents.

### Linter

```bash
make check
cd ~/.claude && markdownlint-cli2 --config .markdownlint-cli2.jsonc "<repo-root>/README.md" "<repo-root>/.claude/skills/sqlcl-conn-mng/SKILL.md" "<repo-root>/docs/tasks/test_folder_filter/*.md"
```

Expected: no ruff, format or mypy findings; no markdownlint errors. Alternatively run `markdownlint-cli2` from `<repo-root>`, which holds its own `.markdownlint-cli2.jsonc`.

### Regression Check

```bash
make unit
```

Expected: all pass, including the unchanged `test_selector_requires_exactly_one` cases for `show`, `delete`, `move`.

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [x] AC-1 - `test --folder /dev` runs SQLcl for exactly the names `list --folder /dev` returns - verified by: `test_test_folder_matches_list`
- [x] AC-2 - `--folder` + `--filter` select the AND of both - verified by: `test_test_folder_and_filter`
- [x] AC-3 - no selector and each forbidden pair exit 2 from `parse_args` and `main` - verified by: `test_test_selector_rules`, `test_test_selector_rules_through_main`
- [x] AC-4 - an empty folder selection exits 1 without SQLcl and names every selector, in the log and the JSON error envelope - verified by: `test_test_folder_empty_message`
- [x] AC-5 - a folder batch prints per-connection lines and summary, the JSON batch envelope, exits 1 on failure, and refuses duplicated names - verified by: `test_test_folder_batch_output`, `test_test_folder_rejects_duplicate_names`
- [ ] AC-6 - 0.6.0 in `pyproject.toml` and `uv.lock`, and `--version` prints it - verified by: Phase 2 verification commands
- [ ] AC-7 - `README.md` and `SKILL.md` document `test --folder`, the AND rule, and the 0.6.0 minimum - verified by: Phase 2 grep and a read of both sections
- [x] AC-8 - `show`, `delete`, `move` selector tests pass unchanged and `move --folder` stays the destination - verified by: `test_selector_requires_exactly_one`, `test_move_folder_is_not_a_selector`, Regression Check
- [x] AC-9 - `--folder /` selects only root-level connections for `list` and `test` - verified by: `test_root_folder_is_root_only`
