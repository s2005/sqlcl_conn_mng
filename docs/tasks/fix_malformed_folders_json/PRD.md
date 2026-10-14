# PRD: Fix Malformed folders.json Crash

## Objective

Make every command report a `folders.json` whose `folders` or `connections` value is not a list as a clean `Malformed folders.json` error with exit code 1, instead of an uncaught `TypeError` traceback.

## Background

`ConnectionStore.folders` (`src/sqlcl_conn_mng/store.py:139`) already turns invalid JSON and a non-object top level into `StoreError`. It does not check the type of the `folders` and `connections` values, so `null`, a number or a boolean reaches a `for` loop in `_build_folder` (`store.py:74-80`) or in `folders()` itself and raises `TypeError`. `main` (`src/sqlcl_conn_mng/cli.py:1018`) catches only `SqlclError`, `StoreError`, `ValueError` and `OSError`, so the user sees a Python traceback from `list`, `show`, `folders`, `export` and every command that resolves a selector. The defect was reproduced on a store built by SQLcl itself (see `analysis.md`). Found by the test gap review in `docs/tasks/test_gap_coverage/` (finding F2).

## Requirements

### REQ-1: Non-list folder values raise StoreError

`ConnectionStore.folders()` raises `StoreError` whose message starts with `Malformed folders.json:` and names the offending key (`folders` or `connections`) and the folder path (or the top level), when:

- the top-level `folders` value is present and not a list;
- a folder's `folders` value is present and not a list;
- a folder's `connections` value is present and not a list.

An absent key keeps today's meaning (empty list). Non-string entries inside a `connections` list keep being skipped as today.

### REQ-2: The CLI exits 1 without a traceback

`sqlcl-conn-mng list` (and any other command reading folders) on such a store logs the `Malformed folders.json: ...` message, prints the JSON error object under `--format json`, and returns exit code 1. No exception escapes `main`.

### REQ-3: README states the behaviour

The "Store format" section of `README.md` says that a `folders.json` that is not valid JSON or whose `folders` or `connections` value is not a list is reported as an error (exit 1).

## Non-Requirements

- Treating `null` as an empty list (rejected in `open_questions.md` Q2).
- Catching `TypeError` in `main` as a general safety net.
- Validating folder names, duplicate folder paths or connection ids that do not exist.
- Unreadable `dbtools.properties` files - task `fix_unreadable_properties_skip`.

## Acceptance Criteria

- **AC-1** - Unit tests for each non-list case (top-level `folders`, nested `folders`, `connections`; values `null`, number, boolean, string) expect `StoreError` with the key and folder in the message, and pass (REQ-1)
- **AC-2** - Existing store tests still pass: an absent key reads as empty, invalid JSON still raises (REQ-1)
- **AC-3** - A CLI test runs `main(["list", ...])` on a store with `"connections": null` and gets exit 1 and the error object under `--format json`, with no exception escaping (REQ-2)
- **AC-4** - The reproduction from `analysis.md` against a SQLcl-built store prints the error line and no traceback (REQ-1, REQ-2)
- **AC-5** - README "Store format" mentions the error, and `markdownlint-cli2` reports no issue (REQ-3)
- **AC-6** - `make check` and `make unit` pass (REQ-1, REQ-2)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| src/sqlcl_conn_mng/store.py | Update |
| tests/test_store.py | Update |
| tests/test_cli.py | Update |
| README.md | Update |
| pyproject.toml, uv.lock | Update (patch bump to 0.9.2, so the fixed release is distinguishable from the defective one) |
