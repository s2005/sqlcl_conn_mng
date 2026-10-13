# Verification Plan: Descriptor connect string quoting

## Purpose

Prove that `add` and `update` save connections with descriptor and `?` parameter connect strings, and that nothing else regressed.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
uv run pytest -q
```

Expected: all unit tests pass (299 passed, 1 skipped on Windows).

## Post-Implementation Verification

### Phase 1: Record the bug with strict xfail tests

Covers REQ-2, REQ-3, REQ-4.

```bash
make db-start
uv run pytest -m integration -q -k "descriptor or parameter"
```

Expected: every new test reports XFAIL. `make db-start` needs `SQLCL_ITEST_PASSWORD` in the environment.

### Phase 2: Fix the quoting

Covers REQ-1, REQ-5.

```bash
uv run pytest -q tests/test_sqlcl.py
```

Expected: pass, including the new command-text tests.

### Phase 3: Flip the markers and bump the version

Covers REQ-2, REQ-3, REQ-4, REQ-6.

```bash
uv run pytest -m integration -q
uv run sqlcl-conn-mng --version
```

Expected: the integration suite passes with no xfail left for this task; the version prints 0.9.1.

### Linter

```bash
make check
```

### Regression Check

```bash
uv run pytest -q
```

## Final Acceptance Verification

The fix can be accepted when all items are true:

- [x] AC-1 - the command text for safe, descriptor and `?` connect strings - verified by: Phase 2 unit tests
- [x] AC-2 - `add` with a descriptor and with a `?` string passes - verified by: Phase 3 integration run
- [x] AC-3 - `update --connect-string` with a descriptor passes - verified by: Phase 3 integration run
- [x] AC-4 - `update --password-env` on stored descriptor and `?` connections passes - verified by: Phase 3 integration run
- [x] AC-5 - version prints 0.9.1 - verified by: `uv run sqlcl-conn-mng --version`
