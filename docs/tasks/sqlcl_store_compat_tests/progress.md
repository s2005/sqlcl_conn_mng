# Progress: Integration Tests for Compatibility with SQLcl-Made Store Entries

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
- [x] Create open_questions.md (Q1-Q4 recommended defaults adopted on 2026-10-08; Q12-Q15 answered by the user on 2026-10-08; Q11 answered by Phase 1 discovery)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Harness, Make Targets and Import Fixture Discovery

Requirements: REQ-1, REQ-8, REQ-10

- [ ] Run the pre-implementation baseline from `verification.md`
- [ ] Create the `Makefile` with `check`, `unit`, `integration`, `sqlcl`, `print-sqlcl-version` and `PYTEST_ARGS`
- [ ] Add `.cache/` to `.gitignore`
- [ ] Create `tests/integration/__init__.py` and `tests/integration/conftest.py`
- [ ] Add `sqlcl_path` and `sqlcl_release` session fixtures with skip on missing SQLcl
- [ ] Add `build_store(stages)` with ordered success-line checks and password masking
- [ ] Add `run_cli`, `snapshot` (via `scripts/store_probe.py`) and `copy_store`
- [ ] Add `db_settings` and `assert_no_password`
- [ ] Discovery: write `tests/integration/data/sqldev_export.json` and confirm `connmgr import` accepts it
- [ ] Record the discovery outcome in `open_questions.md`, Q11, and apply the fallback if it was rejected
- [ ] Write `tests/integration/test_harness_smoke.py`
- [ ] Verify Phase 1 and commit

## Phase 2: Folder and Import Scenarios

Requirements: REQ-2, REQ-3

- [ ] Build the SQLcl folder stores (tree build, deletes)
- [ ] Assert `folders` and `list --folder` against the expected trees
- [ ] Assert the tool's `add-folder`, `move`, `delete-folder` and `delete-folder --force --yes` on a copied store
- [ ] Build the import store with `RENAME` and `REPLACE` duplicates
- [ ] Assert imported values in `list`, `show --check-password` and `export`
- [ ] Record the follow-up "present the connect string of `ORACLE_BASIC` connections" under Follow-Ups
- [ ] Verify Phase 2 and commit

## Phase 3: Connection Operations and Edge-Case Values

Requirements: REQ-4, REQ-5

- [ ] Build the connection-operations store in stages around rename, move and delete
- [ ] Assert id behaviour for rename, move, clone and delete, and clone folder placement
- [ ] Assert case-sensitive lookup for `c1` and `C1`
- [ ] Assert the tool's `rename`, `move`, `clone`, `clone --user`, `clone --no-password`, `delete --yes` on a copied store
- [ ] Build the edge-values store and assert every name, user and folder value
- [ ] Assert the tool-made non-ASCII clone, or commit it as a Windows-only strict `xfail` citing `sqlcl_stdin_encoding`
- [ ] Verify Phase 3 and commit

## Phase 4: Live-Database Scenarios

Requirements: REQ-6, REQ-8, REQ-10

- [ ] Add `ENGINE`, `DB_IMAGE`, `DB_CONTAINER`, `DB_PORT`, the `SQLCL_ITEST_USER` / `SQLCL_ITEST_CONNECT` defaults, `db-start` and `db-stop` to the `Makefile`
- [ ] Confirm `db-start` refuses to run without `SQLCL_ITEST_PASSWORD` and never echoes a password
- [ ] Build the saved-password store in stages, including both `-replace` directions and the descriptor connect string
- [ ] Assert reported values and `password_saved` against SQLcl's `connmgr show`
- [ ] Assert id stability and password state across `-replace`
- [ ] Assert the tool's `test` command on `p_saved`
- [ ] Assert no password in any tool output or export file
- [ ] Verify Phase 4 with and without the password variable, and commit

## Phase 5: Format Conformance

Requirements: REQ-7

- [ ] Make the Phase 2-4 store fixtures session-scoped for reuse
- [ ] Add `assert_format` and its self-test
- [ ] Assert the id rule and per-operation file sets
- [ ] Assert `dbtools.properties` header, line endings, encoding, escaping and key order
- [ ] Assert `folders.json` layout, ordering and the empty-tree form
- [ ] Verify Phase 5 and commit

## Phase 6: GitHub Actions Workflow

Requirements: REQ-11, REQ-10

- [ ] Create `.github/workflows/ci.yml` with the Ubuntu and Windows matrix
- [ ] Add setup steps: uv with Python 3.13, Temurin 17, `choco install make` on Windows
- [ ] Add `make check`, `make unit`, the SQLcl cache keyed by `make -s print-sqlcl-version`, `make sqlcl` and the `GITHUB_PATH` entry
- [ ] Add the Linux-only password generation with `::add-mask::`, `make db-start` and the `always()` `make db-stop`
- [ ] Add `make integration` for both runners
- [ ] Confirm the workflow repeats no command, version or container setting
- [ ] Push, watch the run, and confirm both jobs, database pass on Ubuntu, skip on Windows, masked password, cache hit on rerun
- [ ] Commit

## Phase 7: Documentation and Final Verification

Requirements: REQ-9, REQ-8

- [ ] Update `README.md`, "Development" and "Testing"
- [ ] Run `make check`, `make unit` and `make integration` with and without the database
- [ ] Run the secret and store hygiene checks
- [ ] Run markdown lint on `README.md` and the task folder
- [ ] Tick the final acceptance checklist in `verification.md`
- [ ] Commit

## Follow-Ups

Defects and gaps found by the tests are listed here with their follow-up task (`open_questions.md`, Q6).

- (none yet)
