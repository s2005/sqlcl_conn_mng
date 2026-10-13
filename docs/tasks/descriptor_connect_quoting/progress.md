# Progress: Descriptor connect string quoting

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
- [x] Create open_questions.md
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Record the bug with strict xfail tests

Requirements: REQ-2, REQ-3, REQ-4

- [x] Add the strict xfail integration tests
- [x] Verify they all XFAIL in the podman container

## Phase 2: Fix the quoting

Requirements: REQ-1, REQ-5

- [x] Change `save_connection`
- [x] Add the unit tests
- [x] Run `make check` and the unit tests

## Phase 3: Flip the markers and bump the version

Requirements: REQ-2, REQ-3, REQ-4, REQ-6

- [x] Remove the xfail markers
- [x] Bump the version to 0.9.1 and run `uv lock`
- [x] Run the integration suite in the podman container

## Review Feedback

(Added when PR review feedback arrives.)
