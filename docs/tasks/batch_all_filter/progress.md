# Progress: Batch Selection With --all And --filter

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
- [x] Create open_questions.md (Q1-Q5 answered by the user, Q6 by the version-bump rule)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Selector And Matcher

Requirements: REQ-1, REQ-2, REQ-3

- [x] Run the pre-implementation baseline from `verification.md`
- [x] Add `_add_selector` and apply it to `test`, `show`, `delete`, `move`
- [x] Add `_matches` and `_select_names`
- [x] Extract the per-connection data helper from `_cmd_show`
- [x] Unit tests for selector exclusivity, glob matching, order, unknown `--name`
- [x] `make unit` and `make check` pass

## Phase 2: Batch Runner And Command Wiring

Requirements: REQ-4, REQ-5, REQ-6

- [x] Add `_run_batch` with per-connection lines, summary and exit code
- [x] Rewrite `_cmd_test`, `_cmd_move`, `_cmd_delete`, `_cmd_show` over the batch path
- [x] Unit tests: `--name` unchanged, continue-on-failure, empty match, delete guard, show batch, move batch
- [x] Create `tests/integration/test_batch_compat.py`
- [x] `make unit`, `make check`, `make integration` pass

## Phase 3: list And export Filter

Requirements: REQ-2, REQ-6

- [x] Add `--filter` to `list` and `export`
- [x] Unit tests for both, including the empty result
- [x] `make unit` and `make check` pass

## Phase 4: Documentation And Version Bump

Requirements: REQ-7, REQ-8

- [x] Update `README.md` (table, batch section, examples, exit codes)
- [x] Update `.claude/skills/sqlcl-conn-mng/SKILL.md`
- [x] Set `version = "0.3.0"` in `pyproject.toml` and run `uv lock`
- [x] Reinstall the global tool and confirm `--version` prints `0.3.0`
- [x] `markdownlint-cli2` clean on changed Markdown files

## Review Feedback

(Section appears when PR review feedback arrives. Each comment gets a checkbox.)

## Review Feedback (PR #3)

- [x] P1: Preserve connection identity when selecting duplicate names (fixed - a batch that selects a shared name is refused with `Ambiguous selection`)
