# Open Questions: Fix Malformed folders.json Crash

## Q1: Is there a defect to fix at all?

- **Why it matters**: the task exists only if the crash is real on a store SQLcl itself produced, not only on a hand-made fixture.
- **Options**: (a) reproduce on a store built by SQLcl's own `connmgr import`, then mutate `folders.json`; (b) trust the unit-level probe.
- **Recommended**: (a) - a genuine store rules out a fixture artefact.
- **Answer**: confirmed - on a store built by SQLcl 25.4.1 `connmgr import` plus `connmgr add -folder /dev` and `connmgr move`, setting `connections` or `folders` to `null` makes `sqlcl-conn-mng list` end in an uncaught `TypeError` traceback, while SQLcl prints one error line for `connmgr list` and keeps `connmgr show` working. Evidence in `analysis.md` - decided by reproduction.

## Q2: Should a null list be rejected or read as empty?

- **Why it matters**: decides whether every read command fails (exit 1) or the store is read as if the list were empty.
- **Options**: (a) raise `StoreError("Malformed folders.json: ...")`, exit 1; (b) treat `null` as `[]`.
- **Recommended**: (a) - it matches how the store already treats invalid JSON and a non-object top level (`ConnectionStore.folders`, `src/sqlcl_conn_mng/store.py:146-149`, pinned by `test_malformed_folders_json`). Reading `null` as empty would silently move every connection of that folder to the root, so a later `move` or `copy` would act on a wrong folder.
- **Answer**: (a) - decided by reading `src/sqlcl_conn_mng/store.py:146-149` and `tests/test_store.py:73`.

## Q3: Which value types are covered?

- **Why it matters**: `null` is the reported case; numbers and booleans fail the same way, and a string is iterated character by character.
- **Options**: (a) any non-list `folders` or `connections` value, at the top level and in every nested folder; (b) `null` only.
- **Recommended**: (a) - one check covers the whole defect class (a non-list reaching a `for` loop); limiting it to `null` leaves `5` and `true` crashing the same way.
- **Answer**: (a) - decided by reading `_build_folder`, `src/sqlcl_conn_mng/store.py:74-80`.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | Phase 1 |
| Q2 | Answered | REQ-1 |
| Q3 | Answered | REQ-1 |
