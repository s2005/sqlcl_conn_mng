# Progress: Relative --home Breaks delete and delete-folder

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
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Absolute -home in SqlclRunner

Requirements: REQ-1, REQ-3

- [x] `SqlclRunner.__init__` stores `os.path.abspath(home)`; docstring updated
- [x] Update `test_argv_thin_and_thick` to expect the absolute form
- [x] Add `test_argv_makes_relative_home_absolute`
- [x] Add `test_argv_keeps_absolute_home`
- [x] `uv run pytest tests/test_sqlcl.py -q` and `make check` pass

## Phase 2: Relative-home Integration Tests

Requirements: REQ-2, REQ-3

- [x] Add `test_tool_delete_relative_home`
- [x] Add `test_tool_force_delete_folder_relative_home`
- [x] Confirm both fail without the Phase 1 change, then restore it
- [x] `make integration` passes

## Phase 3: Version and README

Requirements: REQ-4, REQ-5

- [ ] Bump `pyproject.toml` to 0.7.1 and run `uv lock`
- [ ] Amend the README `--home` row
- [ ] `uv run sqlcl-conn-mng --version` prints 0.7.1
- [ ] README lints clean
- [ ] Reinstall the global copy, or record why it was skipped
