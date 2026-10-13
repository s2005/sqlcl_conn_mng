# Progress: Copy Saved Connections Between Homes

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
- [x] Resolve open questions (open_questions.md, Q1-Q8 answered)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Store copy primitive

Requirements: REQ-2

- [x] Add `new_connection_id` to `store.py`
- [x] Add `ConnectionStore.copy_connection_to` with staging directory and atomic rename
- [x] Add `ConnectionStore.remove_connection_dir`
- [x] Store tests in `tests/test_store.py`
- [x] `make check` clean, store tests pass
- [x] Commit phase 1

## Phase 2: `copy` subcommand

Requirements: REQ-1, REQ-3, REQ-4, REQ-5

- [x] Add the `copy` parser with `--to-home`, selector and `--format`
- [x] Implement `_cmd_copy`: same-home check, selection, duplicate refusal
- [x] Per-item name clash check (case-insensitive)
- [x] Folder placement through a lazily built target runner, with rollback on failure
- [x] CLI tests in `tests/test_cli.py`
- [x] `make check` clean, `make unit` passes
- [x] Commit phase 2

## Phase 3: SQLcl acceptance test

Requirements: REQ-2, REQ-3

- [x] Create `tests/integration/test_copy_compat.py`
- [ ] Run with the test database up; confirm the skip message without it
- [x] Commit phase 3

## Phase 4: Documentation and version

Requirements: REQ-6, REQ-7

- [ ] Update `README.md` (commands table, note, batch and JSON lists, example, policy sentences)
- [ ] Update `.claude/skills/sqlcl-conn-mng/SKILL.md`
- [ ] Bump `pyproject.toml` to 0.6.0 and run `uv lock`
- [ ] Reinstall globally and confirm `--version` prints 0.6.0
- [ ] Markdown lint clean
- [ ] Commit phase 4
