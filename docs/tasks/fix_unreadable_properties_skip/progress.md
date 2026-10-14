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

- [x] Run the pre-implementation baseline from `verification.md` (`make check` pass; `make unit` 324 passed, 1 skipped, 167 deselected; Defect Present command prints the Malformed unicode escape error and `rc 1`)
- [x] `test_unparseable_properties_are_skipped_with_one_warning`
- [x] `test_direct_reads_of_unparseable_file_still_raise`
- [x] `test_list_skips_unparseable_connection`
- [x] `test_folders_and_export_skip_unparseable_connection`
- [x] Confirm the skip tests fail (committed as strict xfail; marker removed in Phase 2) with the `Malformed unicode escape` error

## Phase 2: Skip And Warn In The Store

Requirements: REQ-1, REQ-2, REQ-3

- [x] Module logger and `_skipped` set in `store.py`
- [x] `try/except ValueError` in `connections()`, one warning per id
- [x] Docstrings updated
- [x] Phase 1 tests pass (xfail markers removed; 263 passed, 1 skipped)

## Phase 3: Documentation And Gate

Requirements: REQ-4, REQ-5

- [ ] README "Store format" bullet
- [ ] Bump version to 0.9.3 in `pyproject.toml`, `uv lock`
- [ ] `make check`, `make unit`, markdownlint
- [ ] SQLcl-built reproduction lists the readable connections and logs the warning
