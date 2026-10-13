# Verification Plan: Relative --home Breaks delete and delete-folder

## Purpose

Prove that SQLcl always receives an absolute `-home`, that `delete` and `delete-folder --force` work with a relative store path, and that nothing else changes.

## Pre-Implementation Verification

Run from `<repo-root>`.

### Existing Tests Pass

```bash
make check
make unit
make integration
```

Expected: all pass. `make integration` needs SQLcl on PATH or `SQLCL_BIN` set; the tests skip otherwise.

### Defect Reproduces

Build a throwaway store from the import fixture and run `delete` with a relative `--home` from the store's parent:

```bash
mkdir -p "$TMPDIR/relhome" && cd "$TMPDIR/relhome"
printf 'connmgr import "%s"\nexit\n' "$(cygpath -m <repo-root>/tests/integration/data/sqldev_export.json)" | sql -S -nohistory -noupdates -home "$(pwd -W)/st" /nolog
uv run --project <repo-root> sqlcl-conn-mng delete --name imp1 --yes --home st
```

Expected before the fix: exit 1 and a `SEVERE ... validatePermissions` line naming `st\connections\st\connections\<id>`.

## Post-Implementation Verification

### Phase 1: Absolute -home in SqlclRunner

Requirements: REQ-1, REQ-3

```bash
uv run pytest tests/test_sqlcl.py -q
```

Expected: pass, including `test_argv_makes_relative_home_absolute` and `test_argv_keeps_absolute_home`.

### Phase 2: Relative-home Integration Tests

Requirements: REQ-2, REQ-3

```bash
uv run pytest -m integration -q -k relative_home
```

Expected: 2 passed. With the Phase 1 change stashed, the same command gives 2 failed.

### Phase 3: Version and README

Requirements: REQ-4, REQ-5

```bash
uv run sqlcl-conn-mng --version
```

Expected: `0.7.1`. Lint `README.md` with markdownlint-cli2 using the repo's `.markdownlint-cli2.jsonc`; expected clean.

### Linter

```bash
make check
```

Expected: ruff, ruff format and mypy clean.

### Regression Check

```bash
make unit
make integration
```

Expected: all pass, including the existing `copy` tests.

The "Defect Reproduces" commands run again after the fix: exit 0 and `Connection imp1 has been deleted`.

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [x] AC-1 - relative home becomes absolute in `argv()`, absolute home is kept - verified by: Phase 1 unit tests
- [ ] AC-2 - `delete` with a relative `--home` exits 0, removes the connection, no `SEVERE` - verified by: `test_tool_delete_relative_home` and the "Defect Reproduces" rerun
- [ ] AC-3 - `delete-folder --force` with a relative `--home` exits 0 and removes the folder and its connection - verified by: `test_tool_force_delete_folder_relative_home`
- [ ] AC-4 - `copy` message prints `--to-home` as given - verified by: existing `copy` tests in `make unit` and `make integration` passing unchanged
- [ ] AC-5 - `uv run sqlcl-conn-mng --version` prints 0.7.1 - verified by: Phase 3 command
- [ ] AC-6 - README `--home` row says the path is made absolute - verified by: reading `README.md` and the lint run
- [ ] AC-7 - `make check`, `make unit` and `make integration` pass - verified by: Linter and Regression Check sections
