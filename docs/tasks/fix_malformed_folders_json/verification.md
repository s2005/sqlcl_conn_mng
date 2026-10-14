# Verification Plan: Fix Malformed folders.json Crash

## Purpose

Prove that a non-list `folders` or `connections` value in `folders.json` is reported as `Malformed folders.json` with exit 1 and no traceback, and that valid stores read as before.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
make check
make unit
```

Expected: both pass.

### Defect Present

```bash
uv run python -c "import json,tempfile,pathlib; h=pathlib.Path(tempfile.mkdtemp()); c=h/'connections'/('A'*22); c.mkdir(parents=True); (c/'dbtools.properties').write_text('name=good'+chr(10)); (h/'connection_folders').mkdir(); (h/'connection_folders/folders.json').write_text(json.dumps({'folders':[{'name':'dev','connections':None}]})); from sqlcl_conn_mng.cli import main; main(['list','--home',str(h)])"
```

Expected: `TypeError: 'NoneType' object is not iterable` traceback.

## Post-Implementation Verification

### Phase 1: Failing Tests

REQ-1, REQ-2.

```bash
uv run pytest -q tests/test_store.py tests/test_cli.py
```

Expected before Phase 2: the new tests fail; all others pass.

### Phase 2: Type Check In The Store

REQ-1, REQ-2.

```bash
uv run pytest -q tests/test_store.py tests/test_cli.py
```

Expected: all pass. The "Defect Present" command now logs `Malformed folders.json: 'connections' of /dev is not a list` (wording may differ) and prints no traceback.

### Phase 3: Documentation And Gate

REQ-3.

```bash
npx markdownlint-cli2 README.md
```

Expected: no issue. Then repeat the SQLcl-built reproduction from `analysis.md` with `MSYS_NO_PATHCONV=1` in Git Bash: `sqlcl-conn-mng list --home <scratch-store>` prints the error line and exits 1 for each mutation.

### Linter

```bash
make check
```

Expected: pass with no new suppression.

### Regression Check

```bash
make unit
```

Expected: all pass.

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [x] AC-1 - Non-list cases raise `StoreError` naming key and folder - verified by: Phase 2 command
- [x] AC-2 - Absent key and invalid JSON tests still pass - verified by: Regression Check
- [x] AC-3 - CLI exits 1 with the JSON error object, no traceback - verified by: Phase 2 command
- [x] AC-4 - SQLcl-built reproduction shows the error and no traceback - verified by: Phase 3 manual step
- [x] AC-5 - README "Store format" updated and lint clean - verified by: Phase 3 command
- [x] AC-6 - `make check` and `make unit` pass - verified by: Linter, Regression Check
