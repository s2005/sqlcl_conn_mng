# Verification Plan: Skip Unreadable Connection Properties

## Purpose

Prove that one unparseable `dbtools.properties` no longer hides the rest of the store, that the warning names the broken file once, that exit codes and JSON output are unchanged by the skip, and that the broken file is never rewritten.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
make check
make unit
```

Expected: both pass.

### Defect Present

```bash
uv run python -c "import tempfile,pathlib; h=pathlib.Path(tempfile.mkdtemp()); [ (h/'connections'/i).mkdir(parents=True) for i in ('A'*22,'B'*22) ]; (h/'connections'/('A'*22)/'dbtools.properties').write_text('name=bad'+chr(92)+'u12zz'+chr(10)); (h/'connections'/('B'*22)/'dbtools.properties').write_text('name=good'+chr(10)); from sqlcl_conn_mng.cli import main; print('rc', main(['list','--home',str(h)]))"
```

Expected: `[ERROR] ... Malformed unicode escape in properties text: \u12zz` and `rc 1`; `good` not listed.

## Post-Implementation Verification

### Phase 1: Failing Tests

REQ-1, REQ-2, REQ-3.

```bash
uv run pytest -q tests/test_store.py tests/test_cli.py
```

Expected before Phase 2: the skip tests fail; `test_direct_reads_of_unparseable_file_still_raise` passes.

### Phase 2: Skip And Warn In The Store

REQ-1, REQ-2, REQ-3.

```bash
uv run pytest -q tests/test_store.py tests/test_cli.py
```

Expected: all pass. The "Defect Present" command now logs one `[WARNING]` naming `AAAAAAAAAAAAAAAAAAAAAA` and its path, lists `good`, and prints `rc 0`.

### Phase 3: Documentation And Gate

REQ-4, REQ-5.

```bash
npx markdownlint-cli2 README.md
uv run sqlcl-conn-mng --version
```

Expected: no markdown issue; the version command prints 0.9.3.

Then repeat the SQLcl-built reproduction from `analysis.md` with `MSYS_NO_PATHCONV=1` in Git Bash: `sqlcl-conn-mng list --home <scratch-store>` lists `imp1` and `imp3`, logs the warning with `imp2`'s file path, exits 0.

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

- [x] AC-1 - Broken connection skipped, one warning with id and path across repeated calls - verified by: Phase 2 command
- [x] AC-2 - `list`, `folders`, `export` work on the readable connections, valid JSON, exit 0 - verified by: Phase 2 command
- [x] AC-3 - Direct reads of the broken id still raise, file unchanged - verified by: Phase 2 command
- [ ] AC-4 - SQLcl-built reproduction lists the two readable connections and warns with the path - verified by: Phase 3 manual step
- [x] AC-5 - README updated and lint clean - verified by: Phase 3 command
- [ ] AC-6 - `make check` and `make unit` pass - verified by: Linter, Regression Check
- [ ] AC-7 - Version is 0.9.3 - verified by: Phase 3 command
