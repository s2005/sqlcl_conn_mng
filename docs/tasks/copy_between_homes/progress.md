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

- [ ] Add `new_connection_id` to `store.py`
- [ ] Add `ConnectionStore.copy_connection_to` with staging directory and atomic rename
- [ ] Add `ConnectionStore.remove_connection_dir`
- [ ] Store tests in `tests/test_store.py`
- [ ] `make check` clean, store tests pass
- [ ] Commit phase 1

## Phase 2: `copy` subcommand

Requirements: REQ-1, REQ-3, REQ-4, REQ-5

- [ ] Add the `copy` parser with `--to-home`, selector and `--format`
- [ ] Implement `_cmd_copy`: same-home check, selection, duplicate refusal
- [ ] Per-item name clash check (case-insensitive)
- [ ] Folder placement through a lazily built target runner, with rollback on failure
- [ ] CLI tests in `tests/test_cli.py`
- [ ] `make check` clean, `make unit` passes
- [ ] Commit phase 2

## Phase 3: SQLcl acceptance test

Requirements: REQ-2, REQ-3

- [ ] Create `tests/integration/test_copy_compat.py`
- [ ] Run with the test database up; confirm the skip message without it
- [ ] Commit phase 3

## Phase 4: Documentation and version

Requirements: REQ-6, REQ-7

- [ ] Update `README.md` (commands table, note, batch and JSON lists, example, policy sentences)
- [ ] Update `.claude/skills/sqlcl-conn-mng/SKILL.md`
- [ ] Bump `pyproject.toml` to 0.6.0 and run `uv lock`
- [ ] Reinstall globally and confirm `--version` prints 0.6.0
- [ ] Markdown lint clean
- [ ] Commit phase 4
