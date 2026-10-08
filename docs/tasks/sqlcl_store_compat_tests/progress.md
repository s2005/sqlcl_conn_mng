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

- [x] Run the pre-implementation baseline from `verification.md` (93 passed, 1 deselected; integration 1 passed; ruff, format, mypy clean)
- [x] Create the `Makefile` with `check`, `unit`, `integration`, `sqlcl`, `print-sqlcl-version`, `print-sqlcl-dir`, `print-sqlcl-bin` and `PYTEST_ARGS` (`notes.md`, D3)
- [x] Add `.cache/` to `.gitignore`
- [x] Create `tests/integration/__init__.py`, `tests/integration/conftest.py` and `tests/integration/harness.py` (`notes.md`, D5)
- [x] Add `sqlcl_path` and `sqlcl_release` session fixtures with skip on missing SQLcl
- [x] Add `build_store(stages)` with ordered success-line checks and password masking
- [x] Add `run_cli`, `snapshot` (via `scripts/store_probe.py`) and `copy_store`
- [x] Add `db_settings` and `assert_no_password`
- [x] Discovery: write `tests/integration/data/sqldev_export.json` and confirm `connmgr import` accepts it
- [x] Record the discovery outcome in `open_questions.md`, Q11, and apply the fallback if it was rejected
- [x] Write `tests/integration/test_harness_smoke.py`
- [x] Verify Phase 1 and commit

## Phase 2: Folder and Import Scenarios

Requirements: REQ-2, REQ-3

- [x] Build the SQLcl folder stores (tree build, deletes) as session-scoped fixtures in `conftest.py` (`notes.md`, D4)
- [x] Assert `folders` and `list --folder` against the expected trees
- [x] Assert the tool's `add-folder`, `move`, `delete-folder` and `delete-folder --force --yes` on a copied store
- [x] Build the import store with `RENAME` and `REPLACE` duplicates
- [x] Assert imported values in `list`, `show --check-password` and `export`
- [x] Record the follow-up "present the connect string of `ORACLE_BASIC` connections" under Follow-Ups
- [x] Verify Phase 2 and commit

## Phase 3: Connection Operations and Edge-Case Values

Requirements: REQ-4, REQ-5

- [x] Build the connection-operations store in stages around rename, move and delete
- [x] Assert id behaviour for rename, move, clone and delete, and clone folder placement
- [x] Assert case-sensitive lookup for `c1` and `C1`
- [x] Assert the tool's `rename`, `move`, `clone`, `clone --user`, `clone --no-password`, `delete --yes` on a copied store
- [x] Build the edge-values store and assert every name, user and folder value
- [x] Assert the tool-made non-ASCII clone, or commit it as a Windows-only strict `xfail` citing `sqlcl_stdin_encoding` (passes on Windows: Python's cp1252 stdin matches SQLcl's cp1252 decoding here, so no `xfail`)
- [x] Verify Phase 3 and commit

## Phase 4: Live-Database Scenarios

Requirements: REQ-6, REQ-8, REQ-10

- [x] Add `ENGINE`, `DB_IMAGE`, `DB_CONTAINER`, `DB_PORT`, the `SQLCL_ITEST_USER` / `SQLCL_ITEST_CONNECT` defaults, `db-start` and `db-stop` to the `Makefile`
- [x] Confirm `db-start` refuses to run without `SQLCL_ITEST_PASSWORD` and never echoes a password (exit 2 with the variable named; password count 0 in the `db-start` log)
- [x] Build the saved-password store in stages, including both `-replace` directions and the descriptor connect string
- [x] Assert reported values and `password_saved` against SQLcl's `connmgr show`
- [x] Assert id stability and password state across `-replace`
- [x] Assert the tool's `test` command on `p_saved`
- [x] Assert no password in any tool output or export file; keep secret-bearing frames out of pytest tracebacks (`__tracebackhide__`, masked re-raise), because pytest prints the arguments of the frames it shows
- [x] Verify Phase 4 with and without the password variable, and commit (15 passed, 1 strict `xfail` for `descriptor_connect_quoting`; 16 skipped without the password; password count 0 in the run log)

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

- **Connect string of imported connections** (`open_questions.md`, Q6). `connmgr import` writes `ORACLE_BASIC` connections with `host`, `port` and `serviceName` and no `connectionString`, so the tool reports an empty `connect_string` and the three values in `extra` (`tests/integration/test_import_compat.py`). No value is lost, but how the tool should present the connect string of such a connection is undecided. Follow-up task: `oracle_basic_connect_string`.
- **Descriptor connect strings through the tool's `add`** (`open_questions.md`, Q6). `save_connection` (`src/sqlcl_conn_mng/sqlcl.py:225-246`) passes `user@connect` through `quote_arg`, which wraps the whole target in double quotes when the connect string holds parentheses. SQLcl then fails to connect: `sqlcl-conn-mng add --connect-string "(DESCRIPTION=...)"` against the test database exited 1 with `Connection failed`, while the same call with `//localhost:1521/XEPDB1` saved the connection. Quoting only the descriptor (`itest@"(DESCRIPTION=...)"`) works, as the harness does. Committed as a strict `xfail` (`tests/integration/test_saved_password_compat.py::test_tool_add_with_descriptor`). Follow-up task: `descriptor_connect_quoting`.
