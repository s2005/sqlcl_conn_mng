# Progress: Folder Selection For test

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
- [x] Resolve open questions (open_questions.md)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: test --folder selection

Requirements: REQ-1, REQ-2, REQ-3, REQ-4, REQ-7, REQ-8

- [x] Add `_TestSelectorParser` with the post-parse selector rule (exit 2)
- [x] Add `_add_test_selector` (`--name` / `--all` group, `--filter`, `--folder` as `select_folder`)
- [x] Build the `test` subparser with the new parser class and selector helper
- [x] Narrow by `select_folder` then `name_filter` in `_select_connections`
- [x] Name the folder in `_describe_selection`
- [x] Remove `test` from `SELECTOR_COMMANDS`; add the selector rule tests (parse_args and main)
- [x] Add selection, AND, empty-match, batch output and duplicate-name tests for `test --folder`
- [x] Add the `--folder /` root-only pin test for `list` and `test`
- [x] Add the `move --folder` destination regression test
- [x] `make check` and `make unit` pass

## Phase 2: Version and documentation

Requirements: REQ-5, REQ-6

- [x] Bump `pyproject.toml` to 0.6.0 and run `uv lock`
- [x] Update `README.md` (Commands table incl. the `--folder /` root-only note, Batch selection, JSON output, Examples)
- [x] Update `.claude/skills/sqlcl-conn-mng/SKILL.md` (command table, selector paragraph, minimum version, JSON batch line)
- [x] Reinstall the global tool copy if one is installed; `--version` prints 0.6.0
- [x] markdownlint, `make check` and `make unit` pass
