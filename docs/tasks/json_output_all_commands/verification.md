# Verification Plan: JSON Output For All Commands

## Purpose

Prove that the ten status commands emit one valid JSON document under `--format json`, and that nothing changes without it.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
make unit
```

Expected: all pass.

## Post-Implementation Verification

### Per-Phase Verification

#### Phase 1: Option And Emit Helpers

Requirements: REQ-1, REQ-2, REQ-6

```bash
uv run pytest tests/test_cli.py -q
```

Expected: parser tests for the ten commands pass; an invalid `--format` value exits 2.

#### Phase 2: Single-Result Commands

Requirements: REQ-3, REQ-6

```bash
uv run pytest tests/test_cli.py -q
```

Expected: each command's json stdout parses and holds `status`, `command`, `message` and its extra fields.

#### Phase 3: Batch Envelope

Requirements: REQ-4, REQ-6

```bash
uv run pytest tests/test_cli.py -q
make integration
```

Expected: the `results` envelope is correct with a failing item (exit 1); `delete --format json` prints one document; the integration test passes, or skips with a reason when SQLcl is absent.

#### Phase 4: Error Object

Requirements: REQ-5, REQ-6

```bash
uv run pytest tests/test_cli.py -q
```

Expected: error object on stdout, log line on stderr, exit 1; usage errors stay plain text with exit 2.

#### Phase 5: Documentation, Version And Final Checks

Requirements: REQ-7, REQ-8

```bash
sqlcl-conn-mng --version
```

Expected: prints `sqlcl-conn-mng 0.5.0`.

### Linter

```bash
make check
```

Expected: ruff check, ruff format check and mypy clean.

### Regression Check

```bash
make unit
```

Expected: all pass.

## Final Acceptance Verification

The feature can be accepted when all items are true:

- [x] AC-1 - the ten commands accept `table` and `json`, default `table`, exit 2 otherwise - verified by: Phase 1 tests
- [ ] AC-2 - table output and existing tests unchanged - verified by: Regression Check
- [x] AC-3 - single-result commands print the envelope with extra fields - verified by: Phase 2 tests
- [x] AC-4 - batch `--filter` / `--all` print the `results` envelope, exit 1 on failure - verified by: Phase 3 tests
- [ ] AC-5 - caught failures print the error object, keep the stderr log and exit code - verified by: Phase 4 tests
- [ ] AC-6 - `json.loads` of stdout succeeds on every path - verified by: Phase 2, 3 and 4 tests
- [ ] AC-7 - new unit and integration tests pass, lint clean - verified by: Linter and Regression Check
- [ ] AC-8 - README updated, version 0.5.0 - verified by: `sqlcl-conn-mng --version` and README diff
