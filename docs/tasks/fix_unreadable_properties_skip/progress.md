# Progress: Skip Unreadable Connection Properties

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
- [x] Create open_questions.md (Q1 by reproduction, Q2 by the user, Q3-Q5 by reading the code)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Failing Tests

Requirements: REQ-1, REQ-2, REQ-3

- [ ] Run the pre-implementation baseline from `verification.md`
- [ ] `test_unparseable_properties_are_skipped_with_one_warning`
- [ ] `test_direct_reads_of_unparseable_file_still_raise`
- [ ] `test_list_skips_unparseable_connection`
- [ ] `test_folders_and_export_skip_unparseable_connection`
- [ ] Confirm the skip tests fail with the `Malformed unicode escape` error

## Phase 2: Skip And Warn In The Store

Requirements: REQ-1, REQ-2, REQ-3

- [ ] Module logger and `_skipped` set in `store.py`
- [ ] `try/except ValueError` in `connections()`, one warning per id
- [ ] Docstrings updated
- [ ] Phase 1 tests pass

## Phase 3: Documentation And Gate

Requirements: REQ-4

- [ ] README "Store format" bullet
- [ ] `make check`, `make unit`, markdownlint
- [ ] SQLcl-built reproduction lists the readable connections and logs the warning
