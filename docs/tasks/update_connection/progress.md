# Progress: Update Command For Saved Connections

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
- [x] Create open_questions.md (Q3, Q4, Q5, Q10, Q11 answered by the user; Q2 carried by Phase 1)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Discovery Of SQLcl Replace Behavior

Requirements: REQ-4

- [x] Run the pre-implementation baseline from `verification.md`
- [x] Probe `connect -save -replace` with a changed user and a changed connect string in a temporary store
- [x] Probe a failed connect over an existing connection
- [x] Record the answer in `open_questions.md`, Q2
- [x] Confirm or rewrite Phase 3 from the answer

## Phase 2: Properties Writer

Requirements: REQ-2

- [x] Add `format_properties` to `properties.py`
- [x] Add `ConnectionStore.update_properties` and update the docstrings
- [x] Unit tests for escaping and round trip
- [x] Unit tests for key order, untouched files, atomicity, refused file shapes
- [x] `make unit` and `make check` pass

## Phase 3: Update Command

Requirements: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5

- [x] Add the `update` subparser and option rules
- [x] Add `_cmd_update` with validation, password step and file write
- [x] Generalize password reading without changing `add`
- [x] Unit tests for options, ordering, failures, collisions, secret-free output
- [x] `make unit` and `make check` pass

## Phase 4: Integration, Docs And Version

Requirements: REQ-2, REQ-3, REQ-6, REQ-7

- [x] Integration tests in `tests/integration/test_update_compat.py`
- [x] Update `README.md`
- [x] Update `.claude/skills/sqlcl-conn-mng/SKILL.md`
- [x] Bump the version to `0.4.0`, run `uv lock`, reinstall the global tool, confirm `--version`
- [x] Remove Phase 1 probe leftovers
- [x] `make check`, `make unit`, `make integration` and `markdownlint-cli2` pass

## Review Feedback

## Review Feedback (PR #4)

- [x] P1: Password update on an imported connection had an empty connect string (fixed - target derived from host, port and serviceName)
