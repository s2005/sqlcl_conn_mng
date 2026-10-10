# Progress: JSON Output For All Commands

## Status Legend

| Marker | Meaning                   |
| ------ | ------------------------- |
| `[ ]`  | Not started               |
| `[x]`  | Complete                  |
| `[~]`  | In progress               |
| `[!]`  | Blocked or needs decision |
| `[-]`  | Skipped / not applicable  |

## Planning Checklist

- [x] Analyze current behavior.
- [x] Create open_questions.md and settle every question
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Option And Emit Helpers

Requirements: REQ-1, REQ-2, REQ-6

- [x] Add `_add_format` to the ten parsers
- [x] Add `_emit_ok` and `_emit_error`
- [x] Parser and helper unit tests

## Phase 2: Single-Result Commands

Requirements: REQ-3, REQ-6

- [x] Route add, update, rename, clone, add-folder, delete-folder, export through `_emit_ok`
- [x] Route the `--name` branch of `_run_batch` through `_emit_ok`
- [x] Per-command json and table tests

## Phase 3: Batch Envelope

Requirements: REQ-4, REQ-6

- [x] Build the `results` envelope in `_run_batch`
- [x] Print the `Deleting ...` line of `delete` in table mode only
- [x] Batch unit tests
- [x] Integration test with real SQLcl

## Phase 4: Error Object

Requirements: REQ-5, REQ-6

- [ ] Call `_emit_error` from `main`
- [ ] Error-path unit tests, including list, show, folders and usage errors

## Phase 5: Documentation, Version And Final Checks

Requirements: REQ-7, REQ-8

- [ ] README options table and envelope section
- [ ] Bump version to 0.5.0 and run `uv lock`
- [ ] Reinstall any global copy and confirm `--version`
- [ ] `make check` and `make unit` clean

## Review Feedback

(Section appears when PR review feedback arrives. Each comment gets a checkbox.)
