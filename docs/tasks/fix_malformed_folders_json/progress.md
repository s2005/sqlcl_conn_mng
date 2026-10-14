# Progress: Fix Malformed folders.json Crash

## Status Legend

| Marker | Meaning |
| ------ | ------- |
| `[ ]` | Not started |
| `[x]` | Complete |
| `[~]` | In progress |
| `[!]` | Blocked or needs decision |
| `[-]` | Skipped / not applicable |

## Planning Checklist

- [x] Analyze current behavior.
- [x] Reproduce on a SQLcl-built store (`open_questions.md` Q1)
- [x] Create open_questions.md (Q1 by reproduction, Q2-Q3 by reading the code)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Failing Tests

Requirements: REQ-1, REQ-2

- [ ] Run the pre-implementation baseline from `verification.md`
- [ ] `test_non_list_folder_values_raise_store_error` (parametrized)
- [ ] `test_null_folders_json_exits_1_without_traceback`
- [ ] Confirm the new tests fail with `TypeError` or the misleading message

## Phase 2: Type Check In The Store

Requirements: REQ-1, REQ-2

- [ ] `_list_value` helper in `store.py`
- [ ] Use it in `folders()` and `_build_folder`
- [ ] Phase 1 tests pass

## Phase 3: Documentation And Gate

Requirements: REQ-3

- [ ] README "Store format" bullet
- [ ] `make check`, `make unit`, markdownlint
- [ ] SQLcl-built reproduction prints the error and no traceback
